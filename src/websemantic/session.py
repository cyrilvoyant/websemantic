"""Local conversation state and explicit profile acceptance."""

import json
import re
import unicodedata
from dataclasses import replace

from websemantic.core.validation import Parameter, Scenario, validate

PROFILE = {
    "inputs": {
        "length_m": 1500,
        "n_tubes": 2,
        "n_lanes_per_tube": 2,
        "altitude_m": 300,
        "max_depth_m": 80,
        "gradient_percent": 2.0,
        "tunnel_context": "peri-urban",
        "lighting_type": "LED adaptive",
        "ventilation_type": "longitudinal",
        "aux_kw_per_km_tube": 35.0,
        "base_fixed_kw": 40.0,
        "traffic_level": 1.0,
        "morning_peak_hour": 8.0,
        "evening_peak_hour": 18.0,
        "peak_width_h": 1.4,
        "traffic_sensitivity": 0.65,
        "noise_sigma": 0.06,
        "pollution_probability_per_day": 0.05,
        "accident_probability_per_day": 0.015,
        "pollution_sensitivity": 0.55,
        "accident_sensitivity": 0.75,
    },
    "experiment": {
        "start_date": "2025-01-01",
        "n_days": 7,
        "freq_minutes": 60,
        "n_runs": 3,
        "base_seed": 42,
    },
}
PROFILE_SOURCE = "TLS interface defaults @748e053; experiment websemantic quick-demo-v1 (7 days, hourly, 3 runs, seed 42)"


class ClarificationNeeded(ValueError):
    """An ambiguous request was retained without changing the executable scenario."""


class Session:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.scenario = Scenario("", descriptor["tasks"]["supported"][0])
        self.history = []
        self.calls = 0
        self.pending_clarification = None

    def local_intent(self, request):
        """Resolve explicit workflow requests without asking the LLM to invent data."""
        text = ''.join(c for c in unicodedata.normalize('NFD', request.lower()) if not unicodedata.combining(c))
        message = None
        if re.search(r'\b(moins|plus|entre|environ)\b', text) and re.search(r'\b(km|kilometres?|metres?)\b', text):
            self.pending_clarification = 'Une borne ou une approximation ne fixe pas une longueur précise. Indiquez une longueur de calcul (avec m ou km), ou demandez un profil de démonstration.'
            message = self.pending_clarification
        elif 'ajaccio' in text:
            self.propose_profile()
            source = (
                "Ajaccio coastal demonstration proxy, reviewed 2026-10-03. "
                "https://www.insee.fr/fr/metadonnees/geographie/commune/2A004-ajaccio ; "
                "https://www.corse.developpement-durable.gouv.fr/IMG/pdf/210706-dle_finosello_ajacciu.pdf . "
                "Local study site spans 5.5–18 m NGF; 10 m is a chosen proxy, not a city mean or tunnel observation."
            )
            for name, value in (("altitude_m", 10.0), ("tunnel_context", "urban")):
                if name not in self.scenario.inputs or self.scenario.inputs[name].origin != "provided":
                    self.scenario.inputs[name] = Parameter(value, self.descriptor['inputs'][name].get('unit'), 'assumption', source=source)
            self.pending_clarification = None
            message = (
                "Pour un cas urbain littoral à Ajaccio, je propose 10 m d'altitude et un contexte urbain, "
                "à valider avec /v. Ce sont des hypothèses : 10 m n'est ni l'altitude moyenne d'Ajaccio "
                "ni celle d'un tunnel identifié. Les autres valeurs viennent du profil TLS. "
                "Les valeurs que vous avez fournies restent prioritaires. /d affiche les définitions et sources."
            )
        elif re.search(r'\b(prend|prends|utilise|choisis|mets|valide|accepte)\b', text) and re.search(r'moyenn|defaut|profil|hypothes', text):
            self.propose_profile()
            self.accept_profile()
            self.pending_clarification = None
            message = "Les valeurs manquantes sont complétées par le profil TLS et acceptées à votre demande. Ce sont des valeurs de démonstration, pas des moyennes mesurées. /r lance le calcul."
        elif 'mix' in text and 'moyenn' in text:
            self.propose_profile()
            self.accept_profile()
            self.pending_clarification = None
            message = "J'utilise le profil par défaut pour les champs manquants, comme demandé. Je ne fais pas de moyenne entre technologies : les catégories ne se moyennent pas. /d permet de vérifier ce choix, /r de calculer."
        elif re.search(r'(plus|moins).*co[uû]teu|plus.*energet|plus.*energivo', text):
            high = 'moins' not in text
            self.propose_profile()
            for name, value in (("lighting_type", "sodium fixed" if high else "LED adaptive"), ("ventilation_type", "transverse" if high else "natural/low ventilation")):
                self.scenario.inputs[name] = Parameter(value, None, 'assumption', source="TLS @748e053 category coefficients; scenario proposal, not proof of global optimum.")
            self.pending_clarification = None
            message = "Je propose les catégories aux coefficients " + ('élevés' if high else 'faibles') + " dans TLS. /v valide ces hypothèses. Ce choix ne prouve pas un optimum énergétique ni la faisabilité technique."
        if message:
            self.history.append({'user': request, 'assistant': message})
        return message

    def apply(self, request, parsed):
        """Validate the entire extraction before changing state (atomic update)."""
        updates = []
        seen = set()
        task = parsed.get("task")
        if task not in self.descriptor["tasks"]["supported"] + ["unsupported"]:
            raise ValueError("Tache Gemini non reconnue.")
        if task == 'unsupported':
            self.pending_clarification = parsed.get('message') or 'Demande à préciser ; le scénario précédent est conservé.'
            self.history.append({'user': request, 'assistant': self.pending_clarification})
            raise ClarificationNeeded(self.pending_clarification)
        paths = [update["field"] for update in parsed["updates"]]
        if len(paths) != len(set(paths)) or task.startswith("compare configurations"):
            self.pending_clarification = (
                "Votre demande contient plusieurs configurations ou plusieurs valeurs pour un même paramètre. "
                "Le terminal gère actuellement un seul scénario à la fois. "
                "Pour votre comparaison, décrivez d'abord le scénario A, puis le scénario B dans une nouvelle session. "
                "Précisez le type d'éclairage : LED adaptive, LED fixed, mixed ou sodium fixed. "
                "TLS ne possède pas de paramètre d'intensité lumineuse fort/faible dans ce PoC ; "
                "je ne peux donc pas traduire fidèlement cette différence ni conclure lequel est plus sobre. "
                "Aucun paramètre de la configuration courante n'a été modifié. "
                "Pour lever ce blocage, reformulez une demande portant sur un seul scénario."
            )
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
            if group == "inputs" and name == "length_m":
                # Derive length from the quoted source, never from the LLM's unit label.
                matches = re.findall(
                    r"(\d(?:[\d \u00a0\u202f]*\d)?(?:[.,]\d+)?)\s*(km|kilom[eè]tres?|m[eè]tres?|m)\b",
                    evidence,
                    re.IGNORECASE,
                )
                if not matches:
                    numbers = {'un': 1, 'une': 1, 'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10}
                    words = re.findall(r'\b(' + '|'.join(numbers) + r')\s*(km|kilom[eè]tres?|m[eè]tres?|m)\b', evidence, re.IGNORECASE)
                    matches = [(str(numbers[word.lower()]), unit) for word, unit in words]
                if len(matches) != 1:
                    raise ValueError(
                        "Longueur : fournir une preuve avec une valeur et une unite m ou km explicites."
                    )
                original, source_unit = matches[0]
                original = float(re.sub(r'\s', '', original).replace(",", "."))
                factor = 1000 if source_unit.lower().startswith("k") else 1
                value = original * factor
                source = f"Exact normalisation: {original} {source_unit} x {factor} -> unit:M"
                unit = "unit:M"
            elif spec.get("unit") == "unit:NUM" and unit in (
                None,
                "unit:UNITLESS",
                "unit:NUM",
                "tubes",
                "voies",
            ):
                unit = "unit:NUM"
            elif spec.get('unit') == 'unit:UNITLESS' and unit in (None, '1', 'unit:UNITLESS', 'unit:NUM', 'sans dimension', 'dimensionless', 'UNITLESS'):
                unit = 'unit:UNITLESS'
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
            for name, value in PROFILE[group].items():
                if name not in records or records[name].value is None:
                    records[name] = Parameter(
                        value,
                        self.descriptor[group][name].get("unit"),
                        "default",
                        source=PROFILE_SOURCE,
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
