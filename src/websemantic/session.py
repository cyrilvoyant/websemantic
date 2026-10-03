"""Local conversation state and explicit profile acceptance."""

import json
import re
import unicodedata
from dataclasses import replace

from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.units import normalize


class ClarificationNeeded(ValueError):
    """An ambiguous request was retained without changing the executable scenario."""


class Session:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.scenario = Scenario("", descriptor["tasks"]["supported"][0])
        self.history = []
        self.calls = 0
        self.pending_clarification = None
        self.run_requested = False
        self.geographic_pending = False
        self.geographic_context = None
        self.web_reports = []

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
        if re.search(r'\b(prend|prends|utilise|choisis|mets|valide|accepte|calcule|calculer|simule|simuler)\b', text) and re.search(r'moyenn|defaut|profil|hypothes', text):
            self.propose_profile()
            self.accept_profile()
            self.pending_clarification = None
            message = 'Les valeurs manquantes du profil de démonstration sont acceptées à votre demande. Ce ne sont pas des moyennes mesurées. Le calcul demandé attend les contrôles.'
            self.history.append({'user': request, 'assistant': message})
            return message
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
            if rule.get('accept_profile'):
                self.accept_profile()
            message = rule['message']
            self.pending_clarification = message if rule.get('clarify') else None
            self.history.append({'user': request, 'assistant': message})
            return message
        return None

    def apply(self, request, parsed):
        """Validate the entire extraction before changing state (atomic update)."""
        updates = []
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
            value = update["value"]
            unit = update["unit"] or None
            source = None
            if spec["type"] == "int":
                value = int(value)
            elif spec["type"] == "float":
                value = float(value.replace(",", "."))
            value, unit, source = normalize(value, unit, evidence, spec)
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
            getattr(self.scenario, group)[name] = record
        self.history.append({"user": request, "assistant": parsed.get("message", "")})
        self.pending_clarification = None

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
                    records[name] = replace(record, accepted=True)

    def set_value(self, path, text):
        group, name = path.split(".")
        spec = self.descriptor[group][name]
        value = json.loads(text)
        getattr(self.scenario, group)[name] = Parameter(
            value,
            spec.get("unit"),
            "assumption",
            source="Explicit terminal /set",
            accepted=True,
        )

    def result(self):
        return validate(self.scenario, self.descriptor)
