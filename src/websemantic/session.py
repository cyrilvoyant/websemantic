"""Local conversation state and explicit profile acceptance."""

import json
import re
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

    def apply(self, request, parsed):
        """Validate the entire extraction before changing state (atomic update)."""
        updates = []
        seen = set()
        task = parsed.get("task")
        if task not in self.descriptor["tasks"]["supported"] + ["unsupported"]:
            raise ValueError("Tache Gemini non reconnue.")
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
                    r"(\d+(?:[.,]\d+)?)\s*(km|kilom[eè]tres?|m[eè]tres?|m)\b",
                    evidence,
                    re.IGNORECASE,
                )
                if len(matches) != 1:
                    raise ValueError(
                        "Longueur : fournir une preuve avec une valeur et une unite m ou km explicites."
                    )
                original, source_unit = matches[0]
                original = float(original.replace(",", "."))
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
                if record.origin == "default" and record.source == PROFILE_SOURCE:
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
