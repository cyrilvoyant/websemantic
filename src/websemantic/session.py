"""Local conversation state and explicit profile acceptance."""

import json
import re
import unicodedata
from dataclasses import replace

from websemantic.conversation import validate_questions
from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.qualitative import resolve as resolve_qualitative
from websemantic.units import normalize, parse_number


class ClarificationNeeded(ValueError):
    """An ambiguous request was retained without changing the executable scenario."""


class Session:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.scenario = Scenario("", descriptor["tasks"]["supported"][0])
        for group in ("inputs", "experiment"):
            for name, spec in descriptor.get(group, {}).items():
                if spec.get("operational_default") and "default" in spec:
                    getattr(self.scenario, group)[name] = Parameter(
                        value=spec["default"], unit=spec.get("unit"), origin="default",
                        source=spec["operational_default_source"], accepted=True,
                    )
        self.history = []
        self.calls = 0
        self.pending_clarification = None
        self.run_requested = False
        self.geographic_pending = False
        self.geographic_context = None
        self.web_reports = []
        self.questions = []

    def refresh_questions(self):
        blocking = [item['question'] for item in self.questions if item['blocking']]
        if blocking:
            self.pending_clarification = ' '.join(blocking)

    def add_questions(self, questions):
        validated = validate_questions(questions, self.descriptor)
        existing = {item['question'] for item in self.questions}
        self.questions.extend(item for item in validated if item['question'] not in existing)
        self.refresh_questions()

    def request_calculation(self, request):
        text = ''.join(c for c in unicodedata.normalize('NFD', request.lower()) if not unicodedata.combining(c))
        if re.search(r'\b(annule|stop|ne .*pas|sans)\b.*(calcul|simul)|\bne (calcule|simule).*pas', text):
            self.run_requested = False
            return
        if re.match(r'\s*(comment|pourquoi|explique|que signifie|qu.est)', text):
            return
        if re.search(r'\b(calcule|calculer|simule|simuler|estime|estimer|recalcule)\b|\blance.*(calcul|simulation)', text):
            self.run_requested = True
        for pattern in self.descriptor.get("interpretation", {}).get("calculation_intent_patterns", []):
            if re.search(pattern, text):
                self.run_requested = True

    def local_intent(self, request):
        """Common profile acceptance plus optional reviewed model policy."""
        text = ''.join(c for c in unicodedata.normalize('NFD', request.lower()) if not unicodedata.combining(c))
        # Only a standalone, affirmative instruction can accept defaults locally.
        acceptance = (
            r"\s*(?:(?:prends?|accepte|utilise|choisis|mets|valide)\s+"
            r"|(?:calcule|simule)\s+avec\s+)"
            r"(?:les|des)\s+valeurs\s+(?:par\s+defaut|moyennes|du\s+profil(?:\s+de\s+demonstration)?)"
            r"\s*[.!]?\s*"
        )
        if re.fullmatch(acceptance, text) or re.fullmatch(r"\s*(?:prends|utilise|accepte)\s+le\s+reste\s+par\s+defaut\s*[.!]?\s*", text):
            if any(item['blocking'] for item in self.questions):
                self.refresh_questions()
                return self.pending_clarification
            self.propose_profile()
            self.accept_profile()
            self.pending_clarification = None
            message = 'Les valeurs manquantes du profil de démonstration sont acceptées à votre demande. Ce ne sont pas des moyennes mesurées. Le calcul demandé attend les contrôles.'
            self.history.append({'user': request, 'assistant': message})
            return message
        if "?" in text or re.match(r"\s*(pourquoi|comment|explique|que signifie|qu.est)", text) or re.search(r"\b(?:ne|pas|sans|refuse)\b|\bn['’]", text) or re.search(r"\d", text):
            return None
        for rule in self.descriptor.get('interpretation', {}).get('local_rules', []):
            if not all(re.search(pattern, text) for pattern in rule['patterns']):
                continue
            if rule.get('propose_profile'):
                self.propose_profile()
            proposals = rule.get('proposals', {})
            alternative = rule.get('alternative', {})
            if alternative and re.search(alternative['pattern'], text):
                proposals = alternative['proposals']
            for path, value in proposals.items():
                group, name = path.split('.')
                current = getattr(self.scenario, group).get(name)
                if not rule.get('preserve_provided') or current is None or current.origin != 'provided':
                    getattr(self.scenario, group)[name] = Parameter(value, self.descriptor[group][name].get('unit'), 'assumption', source=rule.get('source'))
            message = rule['message']
            self.pending_clarification = message if rule.get('clarify') else None
            self.history.append({'user': request, 'assistant': message})
            return message
        return None

    def apply(self, request, parsed):
        """Validate the entire extraction before changing state (atomic update)."""
        updates = []
        notices = []
        questions = validate_questions(parsed.get('questions', []), self.descriptor)
        seen = set()
        task = parsed.get("task")
        if task not in self.descriptor["tasks"]["supported"] + ["unsupported"]:
            raise ValueError("Tache Gemini non reconnue.")
        if task == 'unsupported':
            self.run_requested = False
            self.pending_clarification = parsed.get('message') or 'Demande à préciser ; le scénario précédent est conservé.'
            self.history.append({'user': request, 'assistant': self.pending_clarification})
            raise ClarificationNeeded(self.pending_clarification)
        paths = [update["field"] for update in parsed["updates"]]
        if len(paths) != len(set(paths)) or task in self.descriptor.get("interpretation", {}).get("comparison_tasks", []):
            self.pending_clarification = self.descriptor.get('interpretation', {}).get('comparison_message',
                'Plusieurs scénarios ou valeurs sont présents. Précisez un seul scénario ; aucun paramètre courant n’a été modifié.')
            self.history.append({"user": request, "assistant": self.pending_clarification})
            raise ClarificationNeeded(self.pending_clarification)
        for update in parsed["updates"]:
            path = update["field"]
            if path in seen:
                raise ValueError("Champ duplique; clarification necessaire.")
            seen.add(path)
            group, name = path.split(".")
            if (
                group not in ("inputs", "experiment")
                or name not in self.descriptor[group]
            ):
                raise ValueError("Champ non declare.")
            evidence = update["evidence"]
            if not evidence or evidence not in request:
                raise ValueError("Preuve absente du nouveau message.")
            spec = self.descriptor[group][name]
            contextual = any(path in question['fields'] for question in self.questions)
            qualitative = resolve_qualitative(evidence, spec, contextual=contextual)
            if qualitative:
                value, source = qualitative
                updates.append((group, name, Parameter(value, spec.get('unit'), 'assumption', evidence, source)))
                symbol = spec.get('display_unit', 'sans unité')
                if symbol == '1':
                    symbol = 'sans unité'
                shown = format(value, 'g') if isinstance(value, (int, float)) else str(value)
                notices.append(f"{spec.get('label', name)} proposé : {shown} ({symbol}), selon la convention déclarée ; à valider. Ce n’est pas une mesure locale.")
                continue
            value = update["value"]
            unit = update["unit"] or None
            source = None
            number_source = None
            if spec["type"] in ("int", "float"):
                value, number_source = parse_number(value, spec["type"])
            value, unit, source = normalize(value, unit, evidence, spec)
            source = '; '.join(part for part in (number_source, source) if part) or None
            updates.append(
                (group, name, Parameter(value, unit, "provided", evidence, source))
            )
        self.scenario = replace(
            self.scenario,
            request=self.scenario.request + "\n" + request,
            task=task,
            inputs=dict(self.scenario.inputs),
            experiment=dict(self.scenario.experiment),
        )
        for group, name, record in updates:
            previous = getattr(self.scenario, group).get(name)
            if previous is None or previous.value != record.value or previous.unit != record.unit:
                self.run_requested = True
            getattr(self.scenario, group)[name] = record
        if notices:
            parsed['message'] = ' '.join(notices)
        self.history.append({"user": request, "assistant": parsed.get("message", ""), "questions": questions})
        self.pending_clarification = None
        answered = {f'{group}.{name}' for group, name, _ in updates}
        self.questions = [question for question in self.questions if not answered.intersection(question['fields'])]
        self.add_questions(questions)

    def propose_profile(self):
        for group in ("inputs", "experiment"):
            records = getattr(self.scenario, group)
            for name, spec in self.descriptor.get(group, {}).items():
                if "default" not in spec:
                    continue
                value = spec["default"]
                if name not in records or records[name].value is None:
                    records[name] = Parameter(
                        value,
                        self.descriptor[group][name].get("unit"),
                        "default",
                        source=spec.get("default_source", self.descriptor.get("profile", {}).get("source")),
                    )

    def accept_profile(self):
        for group in ("inputs", "experiment"):
            records = getattr(self.scenario, group)
            for name, record in list(records.items()):
                if record.origin in ('default', 'assumption') and record.source:
                    if not record.accepted:
                        self.run_requested = True
                    records[name] = replace(record, accepted=True)

    def set_value(self, path, text):
        group, name = path.split(".")
        if group not in ('inputs', 'experiment'):
            raise ValueError('Groupe de paramètres inconnu.')
        spec = self.descriptor[group][name]
        value = json.loads(text)
        self.run_requested = True
        getattr(self.scenario, group)[name] = Parameter(
            value,
            spec.get("unit"),
            "assumption",
            source="Explicit terminal /set",
            accepted=True,
        )
        self.questions = [question for question in self.questions if path not in question['fields']]
        self.pending_clarification = None
        self.refresh_questions()

    def result(self):
        return validate(self.scenario, self.descriptor)
