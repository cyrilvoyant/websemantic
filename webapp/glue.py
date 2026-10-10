"""WebSemantic in the browser (Pyodide): the deterministic half of each conversation turn.

Only the original, validated codes compute (TLS, LQL-Equiv, pinned and sha256-checked through the reviewed adapters).
The language model only translates the visitor's message into variables of the contract; here, locally:
- nothing is accepted on the visitor's behalf; a calculation starts only on a pure confirmation ("yes", "compute"),
  never in the same turn as a change, a restriction, a request to wait or a question;
- every translated value is checked: exact parameter names only, numbers present in the quoted words, declared
  conventions and defaults taken from the descriptor (never a number chosen by the model);
- anything that cannot be used blocks the calculation and is explained;
- if the message could not be read, nothing changes.
"""

import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd

from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.qualitative import resolve
from websemantic.registry import execute, load_descriptor
from websemantic.units import NUMBER_WORDS, normalize, parse_number

WS = Path(os.environ.get("WEBSEMANTIC_WS", "/home/pyodide/ws"))
CODES = ("tls", "lql")
DESC = {m: load_descriptor(WS, m) for m in CODES}
SINGLE_TASK = {m: DESC[m]["tasks"]["supported"][0] for m in CODES}
MAX_DAYS, MAX_RUNS, MAX_POINTS = 366, 10, 366 * 96 * 10  # one year at 15 min, 10 runs: keeps the browser responsive
NBSP = chr(0x00A0)
NAME = re.compile(r"^[a-z_][a-z0-9_]*$")

T = {
    "en": {
        "explain": {"missing": "no value yet", "unaccepted_assumption": "proposed, waiting for your agreement",
                    "unsupported_origin": "origin not allowed", "evidence": "quote not found in your message",
                    "unit": "not the canonical unit", "bounds": "outside the declared bounds",
                    "category": "not an allowed category", "type": "wrong type", "finite": "must be finite",
                    "unknown_field": "not a parameter of this code", "conflict": "conflicting values",
                    "unsupported_task": "outside what the code supports"},
        "computed": "The pinned code has run on the accepted values. Results are on the right.",
        "refused": "This request is outside what the code supports, so nothing is computed.",
        "not_here": "This kind of request (for instance a comparison of several schedules) is not available on this "
                    "page. Nothing was changed or computed.",
        "needed": "Still needed: **{}**.",
        "conventions": "From your words I propose {}.",
        "defaults": "The other {} parameters take the code's default values (see Variables).",
        "pending": "Reply **yes** to accept everything, or give your own values. Nothing is computed before that.",
        "ready": "Everything is stated or accepted. Reply **yes** to run the calculation.",
        "accepted_some": "Accepted: {}. The other proposals are still waiting.",
        "noted": "Noted from your words: {}.",
        "unchanged": "No value was changed by this message.",
        "blocked": "Still unresolved: **{}** (your last request for it could not be applied). Give the value you want, "
                   "or say **keep** to leave the current value; nothing is computed before that.",
        "kept": "Understood: {} keeps its current value.",
        "not_named": " — this parameter was not named in your message: please check",
        "held": "Understood: nothing is computed for now.",
        "fix": "To fix: {}.",
        "unused": "I could not use: {}. Nothing is computed until this is clarified.",
        "unread": "I could not read your message right now (language service busy or unavailable). Nothing was changed "
                  "or computed; please try again, or reply **yes** to confirm the scenario already shown.",
        "limit": "In the browser, simulations are limited to {} days, {} Monte Carlo runs and about {:,} time points: "
                 "please reduce the period or the number of runs.",
        "failed_run": "The code refused this scenario: {}",
        "example_done": "Example computed without the language model: every value is stated and accepted (see Variables).",
        "not_computable": "not computable",
        "status": ("stated by you", "accepted", "proposed, to accept"),
        "period": "Default period in the browser (7 days, 5 runs); change it in the chat (up to one year, 10 runs)",
        "tls_analysis": "Over {days} simulated days the median peak power is {peak:,.0f} kW and the mean {mean:,.0f} kW "
                        "(load factor {lf:.2f}); the representative run peaks around {hour}:00. In that run, energy "
                        "splits into lighting {li:.0f} %, ventilation {ve:.0f} % and auxiliaries {au:.0f} %. The 10–90 % "
                        "band between Monte Carlo runs has a mean width of {band:.0f} % of the median. ",
        "annual_extrapolated": "The annual figure ({ann:,.0f} MWh/yr) extrapolates the period by 365/{days}; it is not "
                               "a seasonally complete year.",
        "annual_full": "The annual figure ({ann:,.0f} MWh/yr) comes from a simulated year with its seasons.",
        "lql_analysis": "A physical dose of {phys} Gy corresponds to an EQD2 of {eqt} Gy for the target and {eqo} Gy "
                        "for the organ at risk, over {days} days. The model gives a tumour control probability of {tcp} % "
                        "and a complication probability of {ntcp} %. These are model outputs for a fictitious scenario "
                        "with the parameters of the code's library; they do not support any clinical decision.",
    },
    "fr": {
        "explain": {"missing": "pas encore de valeur", "unaccepted_assumption": "proposé, en attente de votre accord",
                    "unsupported_origin": "origine non admise", "evidence": "citation absente de votre message",
                    "unit": "pas l'unité canonique", "bounds": "hors des bornes déclarées",
                    "category": "catégorie non admise", "type": "type incorrect", "finite": "doit être fini",
                    "unknown_field": "pas un paramètre de ce code", "conflict": "valeurs contradictoires",
                    "unsupported_task": "hors du périmètre du code"},
        "computed": "Le code figé a tourné sur les valeurs acceptées. Les résultats sont à droite.",
        "refused": "Cette demande sort du périmètre du code : rien n'est calculé.",
        "not_here": "Ce type de demande (par exemple une comparaison de plusieurs schémas) n'est pas disponible sur "
                    "cette page. Rien n'a été modifié ni calculé.",
        "needed": "Il manque encore : **{}**.",
        "conventions": "D'après vos mots, je propose {}.",
        "defaults": "Les {} autres paramètres reprennent les valeurs par défaut du code (voir Variables).",
        "pending": "Répondez **oui** pour tout accepter, ou donnez vos propres valeurs. Rien n'est calculé avant.",
        "ready": "Tout est donné ou accepté. Répondez **oui** pour lancer le calcul.",
        "accepted_some": "Accepté : {}. Les autres propositions restent en attente.",
        "noted": "Noté d'après vos mots : {}.",
        "unchanged": "Ce message n'a changé aucune valeur.",
        "blocked": "Reste en suspens : **{}** (votre dernière demande n'a pas pu être appliquée). Donnez la valeur "
                   "voulue, ou dites **garder** pour conserver la valeur actuelle ; rien n'est calculé avant.",
        "kept": "Entendu : {} garde sa valeur actuelle.",
        "not_named": " — paramètre non nommé dans votre message : vérifiez",
        "held": "Entendu : rien n'est calculé pour l'instant.",
        "fix": "À corriger : {}.",
        "unused": "Je n'ai pas pu utiliser : {}. Rien n'est calculé tant que ce n'est pas précisé.",
        "unread": "Je n'ai pas pu lire votre message (service de langage occupé ou indisponible). Rien n'a été modifié "
                  "ni calculé ; réessayez, ou répondez **oui** pour confirmer le scénario déjà affiché.",
        "limit": "Dans le navigateur, les simulations sont limitées à {} jours, {} tirages Monte Carlo et environ {:,} "
                 "points de temps : réduisez la période ou le nombre de tirages.",
        "failed_run": "Le code a refusé ce scénario : {}",
        "example_done": "Exemple calculé sans modèle de langage : toutes les valeurs sont données et acceptées (voir Variables).",
        "not_computable": "non calculable",
        "status": ("donné par vous", "accepté", "proposé, à accepter"),
        "period": "Période par défaut dans le navigateur (7 jours, 5 tirages) ; modifiable dans la conversation "
                  "(jusqu'à un an, 10 tirages)",
        "tls_analysis": "Sur {days} jours simulés, la puissance de pointe médiane est {peak:,.0f} kW et la moyenne "
                        "{mean:,.0f} kW (facteur de charge {lf:.2f}) ; le tirage représentatif culmine vers {hour} h. Dans "
                        "ce tirage, l'énergie se répartit entre éclairage {li:.0f} %, ventilation {ve:.0f} % et "
                        "auxiliaires {au:.0f} %. La bande 10–90 % entre tirages Monte Carlo a une largeur moyenne de "
                        "{band:.0f} % de la médiane. ",
        "annual_extrapolated": "Le chiffre annuel ({ann:,.0f} MWh/an) extrapole la période par 365/{days} ; ce n'est "
                               "pas une année complète avec ses saisons.",
        "annual_full": "Le chiffre annuel ({ann:,.0f} MWh/an) vient d'une année simulée avec ses saisons.",
        "lql_analysis": "Une dose physique de {phys} Gy correspond à une EQD2 de {eqt} Gy pour la cible et de {eqo} Gy "
                        "pour l'organe à risque, sur {days} jours. Le modèle donne une probabilité de contrôle tumoral de "
                        "{tcp} % et de complication de {ntcp} %. Ce sont des sorties de modèle pour un scénario fictif, "
                        "avec les paramètres de la bibliothèque du code ; elles ne fondent aucune décision clinique.",
    },
}
LABELS = {  # name: (English, French, unit shown)
    "length_m": ("tunnel length", "longueur du tunnel", "m"), "n_tubes": ("tubes", "tubes", ""),
    "n_lanes_per_tube": ("lanes per tube", "voies par tube", ""), "altitude_m": ("altitude", "altitude", "m"),
    "max_depth_m": ("maximum cover", "couverture maximale", "m"), "gradient_percent": ("gradient", "pente", "%"),
    "tunnel_context": ("setting", "contexte", ""), "lighting_type": ("lighting", "éclairage", ""),
    "ventilation_type": ("ventilation", "ventilation", ""),
    "aux_kw_per_km_tube": ("auxiliary load", "charge des auxiliaires", "kW/(km·tube)"),
    "base_fixed_kw": ("fixed load", "charge fixe", "kW"), "traffic_level": ("traffic level", "niveau de trafic", "× reference"),
    "morning_peak_hour": ("morning peak", "pointe du matin", "h"), "evening_peak_hour": ("evening peak", "pointe du soir", "h"),
    "peak_width_h": ("peak width", "largeur des pointes", "h"),
    "traffic_sensitivity": ("traffic sensitivity", "sensibilité au trafic", ""),
    "noise_sigma": ("random variability", "variabilité aléatoire", ""),
    "pollution_probability_per_day": ("pollution events per day", "épisodes de pollution par jour", ""),
    "accident_probability_per_day": ("accidents per day", "accidents par jour", ""),
    "pollution_sensitivity": ("pollution sensitivity", "sensibilité à la pollution", ""),
    "accident_sensitivity": ("accident sensitivity", "sensibilité aux accidents", ""),
    "start_date": ("start date", "date de début", ""), "n_days": ("simulated period", "période simulée", "days"),
    "freq_minutes": ("time step", "pas de temps", "min"), "n_runs": ("Monte Carlo runs", "tirages Monte Carlo", ""),
    "base_seed": ("random seed", "graine aléatoire", ""),
    "organ": ("organ at risk", "organe à risque", ""), "tumour_site": ("tumour site", "site tumoral", ""),
    "dose_per_fraction": ("dose per session", "dose par séance", "Gy"), "n_fractions": ("number of sessions", "nombre de séances", ""),
    "gap_days": ("treatment gap", "interruption", "days"), "reference_dose": ("reference dose", "dose de référence", "Gy"),
    "bifractionated": ("two sessions a day", "deux séances par jour", ""), "scenario_scope": ("scope", "cadre", ""),
}
SHORT = {  # short words that name a field in a partial consent ("yes, only the length"); full labels also count
    "length_m": ("length", "longueur"), "traffic_level": ("traffic", "trafic"), "n_tubes": ("tube",),
    "n_lanes_per_tube": ("lanes", "voies"), "gradient_percent": ("slope", "pente"),
    "n_days": ("period", "duration", "période", "durée"), "n_runs": ("runs", "tirages"),
    "freq_minutes": ("step", "pas"), "dose_per_fraction": ("dose",), "n_fractions": ("sessions", "séances"),
}
UNIT_FR = {"days": "jours", "× reference": "× référence"}
SOURCES = {"en": {"provided": "your words: “{}”", "convention": "declared convention of the code for “{}”",
                  "default": "declared default of the code", "read": "read by the language model, to confirm"},
           "fr": {"provided": "vos mots : « {} »", "convention": "convention déclarée du code pour « {} »",
                  "default": "valeur par défaut du code", "read": "lu par le modèle de langage, à confirmer"}}
ERRORS = {"en": {"path": "{}: several courses or nested fields are not available here",
                 "unknown": "{}: not a parameter of this code", "number": "{}: the number does not match your words",
                 "level": "{}: no declared convention for these words", "default": "{}: no declared default",
                 "value": "{}: value not usable", "twice": "{}: two different readings in one message",
                 "relative": "{}: your words give a change that I cannot check exactly; please give the final value"},
          "fr": {"path": "{} : plusieurs cures ou champs imbriqués ne sont pas disponibles ici",
                 "unknown": "{} : pas un paramètre de ce code", "number": "{} : le nombre ne correspond pas à vos mots",
                 "level": "{} : pas de convention déclarée pour ces mots", "default": "{} : pas de valeur par défaut déclarée",
                 "value": "{} : valeur inutilisable", "twice": "{} : deux lectures différentes dans le même message",
                 "relative": "{} : vos mots donnent une variation que je ne peux pas vérifier exactement ; indiquez la "
                             "valeur finale"}}

# ---------------------------------------------------------------- formatting


def localise(text, lang):
    if lang != "fr":
        return text
    return re.sub(r"\d[\d,]*\.?\d*", lambda m: m.group(0).replace(",", NBSP).replace(".", ","), text)


def label(name, lang):
    en, fr, _ = LABELS.get(name, (name, name, ""))
    return fr if lang == "fr" else en


def shown(name, value, lang):
    unit = LABELS.get(name, ("", "", ""))[2]
    unit = UNIT_FR.get(unit, unit) if lang == "fr" else unit
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = f"{value:,}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
    return localise(f"{text} {unit}".strip(), lang)


def num(value, fmt, lang):
    """Formatted native number, or 'not computable' when the code returned none."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return T[lang]["not_computable"]
    return localise(format(value, fmt), lang)

# ---------------------------------------------------------------- scenario state


def fresh(model, lang="en"):
    desc = DESC[model]
    state = {"request": "", "task": SINGLE_TASK[model], "inputs": {}, "experiment": {}}
    for group in ("inputs", "experiment"):
        for name, spec in (desc.get(group) or {}).items():
            if spec.get("operational_default") and "default" in spec:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default",
                                          evidence=None, source=spec.get("operational_default_source"), accepted=True)
    if model == "tls":
        for name, value in (("n_days", 7), ("n_runs", 5)):
            state["experiment"][name] = dict(value=value, unit=desc["experiment"][name].get("unit"), origin="default",
                                             evidence=None, source=T[lang]["period"], accepted=False, kind="default")
    return state


def group_of(model, name):
    desc = DESC[model]
    return "experiment" if name in (desc.get("experiment") or {}) else "inputs" if name in desc["inputs"] else None


def to_scenario(state):
    groups = {g: {n: Parameter(**{k: r.get(k) for k in ("value", "unit", "origin", "evidence", "source")},
                               accepted=bool(r.get("accepted")), conflicts=tuple(r.get("conflicts") or ()))
                  for n, r in (state.get(g) or {}).items()} for g in ("inputs", "experiment")}
    return Scenario(state.get("request", ""), state.get("task", ""), groups["inputs"], groups["experiment"])


def check(model, state, lang="en"):
    res = validate(to_scenario(state), DESC[model])
    return {"decision": res.decision, "issues": [{"parameter": i.field, "code": i.code,
                                                   "message": T[lang]["explain"].get(i.code, i.message)}
                                                  for i in res.issues]}


def declared_levels(spec):
    scale = spec.get("qualitative_scale") or {}
    out = {}
    for name, level in (scale.get("levels") or {}).items():
        value = level["value"] if "value" in level else scale.get("reference_upper", 0) * level.get("fraction", 0)
        out[name] = int(value) if spec.get("type") == "int" else float(value)
    return out


def propose_defaults(model, state):
    for group in ("inputs", "experiment"):
        for name, spec in (DESC[model].get(group) or {}).items():
            if name not in state[group] and spec.get("default") is not None:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None,
                                          source="Declared default of the code, proposed", accepted=False, kind="default")


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower()) if not unicodedata.combining(c))


ENGLISH_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30}


def evidence_numbers(evidence):
    """Numbers explicitly present in the quoted words (digits, French and English number words)."""
    text = fold(evidence)
    found = {float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text.replace(NBSP, ""))}
    for word, value in {**NUMBER_WORDS, **ENGLISH_WORDS}.items():
        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text):
            found.add(float(value))
    if re.search(r"\b(sans|aucune?|without|no|none)\b", text):  # "sans interruption", "no gap": zero
        found.add(0.0)
    base = set(found)  # exact calendar conversions: 1 week = 7 days, 1 year = 365 days (no months: not exact)
    if re.search(r"\b(semaines?|weeks?)\b", text):
        found |= {7 * x for x in base} | ({7.0} if not base else set())
    if re.search(r"\b(annees?|years?|ans)\b|\b(un|1) an\b", text):
        found |= {365 * x for x in base} | ({365.0} if not base else set())
    return found


def same(a, b):
    try:
        return a is not None and b is not None and float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def in_words(value, evidence):
    try:
        return float(value) in evidence_numbers(evidence)
    except (TypeError, ValueError):
        return fold(value) in fold(evidence)


UP = re.compile(r"\b(plus|augmente\w*|ajoute\w*|supplementaires?|more|increase\w*|higher|add|added|extra)\b|\+")
DOWN = re.compile(r"\b(moins|reduit\w*|reduire|baisse\w*|diminue\w*|less|decrease\w*|lower|reduce\w*|fewer)\b")
RELATIVE = re.compile(UP.pattern + "|" + DOWN.pattern)


def relative_change(old, value, evidence):
    """A change stated relative to the current value ('200 m de plus'): exact only if value = current ± a stated number."""
    try:
        before, after = float(old["value"]), float(value)
    except (TypeError, ValueError, KeyError):
        return None
    text = fold(evidence)
    for x in sorted(evidence_numbers(evidence)):
        if UP.search(text) and math.isclose(after, before + x):
            return before, "+", x
        if DOWN.search(text) and math.isclose(after, before - x):
            return before, "−", x
    return None


def apply_value(model, state, v, message, lang):
    """One translated value, checked locally. Returns an error text when it cannot be used (nothing changes then)."""
    e = ERRORS[lang]
    raw_name = str(v.get("field") or "")
    if not NAME.match(raw_name):
        return e["path"].format(raw_name)
    group = group_of(model, raw_name)
    if group is None:
        return e["unknown"].format(raw_name)
    name, spec = raw_name, DESC[model][group][raw_name]
    origin, evidence, raw, unit = v.get("origin"), str(v.get("evidence") or ""), v.get("value"), v.get("unit")
    old = state[group].get(name)
    quoted = bool(evidence) and evidence in message
    if old and same(raw, old.get("value")) and not (quoted and in_words(raw, evidence)):
        return None  # the current value repeated without being stated in the message: no change
    if old and (old.get("origin") == "provided" or old.get("accepted")) and not quoted:
        return None  # a later message that does not state this value never overrides it
    try:
        if origin == "convention":
            if not (evidence and evidence in message):
                return e["level"].format(label(name, lang))
            declared = resolve(evidence, spec)  # the descriptor's own resolver first (declared expressions)
            if declared is not None:
                value, source = declared
            else:  # words outside the declared expressions (e.g. English): the model's level, to be accepted
                levels = declared_levels(spec)
                level = str(v.get("level") or "")
                if level not in levels:
                    return e["level"].format(label(name, lang))
                value = levels[level]
                source = (f"Declared convention of the code: '{evidence}' read as level '{level}' = {value}. "
                          "Proposed, to accept; not a measurement.")
            rec = dict(value=value, unit=spec.get("unit"), origin="assumption", evidence=None, accepted=False,
                       said=evidence, kind="convention", source=source)
        elif origin == "default":
            if spec.get("default") is None:
                return e["default"].format(label(name, lang))
            rec = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None, accepted=False,
                       kind="default", source="Declared default of the code, proposed")
        elif origin == "provided":
            numeric = spec.get("type") in ("int", "float")
            value, source = parse_number(raw, spec["type"]) if numeric else (raw, None)
            change = None
            if numeric and not spec.get("evidence_conversion"):  # with a declared conversion, normalize() reads the
                stated = evidence_numbers(evidence)                 # number and unit from the quoted words itself
                if not stated or float(value) not in stated:
                    change = relative_change(old, value, evidence) if old else None
                    if change is None:
                        return e["relative" if RELATIVE.search(fold(evidence)) else "number"].format(label(name, lang))
            value, unit, conv = normalize(value, unit, evidence, spec)
            if not (evidence and evidence in message):
                return e["value"].format(label(name, lang))
            source = "; ".join(s for s in (source, conv) if s) or None
            rec = dict(value=value, unit=unit, origin="provided", evidence=evidence, source=source, accepted=False)
            if change:  # exact arithmetic on a stated number, shown to the visitor
                before, sign, x = change
                rec["relative"] = f"{shown(name, before, lang)} {sign} {shown(name, x, lang)}"
                rec["source"] = f"Exact change stated relative to the current value: {rec['relative']}"
        else:
            return e["value"].format(label(name, lang))
    except (ValueError, TypeError):
        return e["value"].format(label(name, lang))
    state[group][name] = rec
    return None

# ---------------------------------------------------------------- what the message asks (deterministic guards)


PURE = re.compile(r"^\s*(oui|yes|ok|okay|d'accord|d’accord|daccord|j'accepte|j’accepte|j'accepte tout|j’accepte tout|"
                  r"i accept|i accept all|accept all|accept everything|tout accepter|accepte tout|vas-y|go|go ahead|"
                  r"valide|je valide|c'est bon|c’est bon|parfait|sure|fine|calcule|calcule-le|lance le calcul|lance|"
                  r"compute|run|run it|recalcule|recompute)(\s*[,;]?\s*(calcule|lance le calcul|compute|run it|go|vas-y))?"
                  r"\s*[.!]*\s*$", re.IGNORECASE)
HOLD = re.compile(r"\b(attends|attendez|wait|hold on|pas encore|not yet|ne calcule pas|don't compute|do not compute|"
                  r"sans calculer|without computing|stop)\b", re.IGNORECASE)
ONLY = re.compile(r"\b(seulement|uniquement|only|just|sauf|except|mais|but)\b", re.IGNORECASE)
ACCEPT_WORD = re.compile(r"\b(oui|yes|ok|okay|d'accord|d’accord|accepte|j'accepte|j’accepte|accept|agree|valide)\b",
                         re.IGNORECASE)
KEEP = re.compile(r"\b(garde|garder|gardez|conserve|conserver|laisse|laisser|annule|annuler|keep|leave|cancel)\b",
                  re.IGNORECASE)


def names(fields, lang):
    return ", ".join(label(f, lang) for f in fields)


def is_pure_confirmation(message):
    return bool(PURE.match(message))


def named_fields(model, state, message):
    text = fold(message)
    out = []
    for group in ("inputs", "experiment"):
        for name in state[group]:
            en, fr, _ = LABELS.get(name, (name, name, ""))
            words = (name, en, fr) + SHORT.get(name, ())
            if any(re.search(r"(?<!\w)" + re.escape(fold(x)) + r"(?!\w)", text) for x in words):
                out.append((group, name))
    return out


def pending(state):
    return [(g, n) for g in ("inputs", "experiment") for n, r in state[g].items()
            if r.get("origin") in ("assumption", "default") and not r.get("accepted")
            and r.get("source") and r.get("value") is not None]


def over_limit(model, state):
    if model != "tls":
        return False
    exp = state["experiment"]
    days = exp.get("n_days", {}).get("value") or 0
    runs = exp.get("n_runs", {}).get("value") or 0
    step = exp.get("freq_minutes", {}).get("value") or 15
    points = days * 1440 / max(step, 1) * runs
    return days > MAX_DAYS or runs > MAX_RUNS or points > MAX_POINTS

# ---------------------------------------------------------------- results (native values only)


def qualification(target, model):
    m = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    sw = m.get("software", {})
    q = {"software": {k: sw.get(k) for k in ("name", "version", "repository", "commit", "doi", "licence")},
         "nature": m.get("nature"), "uncertainty": m.get("uncertainty") or {},
         "validity_notes": m.get("validity_notes") or [], "note": m.get("note"),
         "verification": (m.get("source_verification") or {}).get("method"),
         "options": {k: str(v) for k, v in (m.get("backend_options") or {}).items()}}
    if model == "lql":
        row = pd.read_csv(target / "indicators.csv").iloc[0].to_dict()
        q["flags"] = {k: bool(row[k]) for k in ("oar_total_valid", "tumour_total_valid", "oar_saturated",
                                                "tumour_saturated") if k in row}
    return q


def files_of(target, names):
    return {n: (target / n).read_text(encoding="utf-8") for n in names if (target / n).exists()}


def tls_results(target, state, lang):
    env = pd.read_csv(target / "envelope.csv")
    rep = pd.read_csv(target / "representative.csv", parse_dates=["timestamp"])
    k = pd.read_csv(target / "kpis.csv").median(numeric_only=True)
    cols = ("lighting_kw", "ventilation_kw", "auxiliary_kw")
    hourly = rep.groupby(rep.timestamp.dt.hour)[list(cols)].mean()
    shares = [float(rep[c].sum()) for c in cols]
    total = sum(shares) or float("nan")
    band = ((env.p90 - env.p10) / env["median"].where(env["median"] != 0)).mean() * 100
    days = state["experiment"].get("n_days", {}).get("value")
    annual = T[lang]["annual_full" if days and days >= 365 else "annual_extrapolated"]
    analysis = localise((T[lang]["tls_analysis"] + annual).format(
        days=days, peak=k.peak_kw, mean=k.mean_kw, lf=k.load_factor, hour=int(hourly.sum(axis=1).idxmax()),
        li=100 * shares[0] / total, ve=100 * shares[1] / total, au=100 * shares[2] / total, band=float(band),
        ann=k.annualized_mwh), lang)
    kpis = [num(k.annualized_mwh, ",.0f", lang), num(k.peak_kw, ",.0f", lang), num(k.load_factor, ".2f", lang),
            num(k.specific_kwh_m_year, ",.0f", lang)]
    return {"kind": "tls", "kpis": kpis, "analysis": analysis, "qualification": qualification(target, "tls"),
            "series": {"t": env.timestamp.tolist(), "median": env["median"].round(2).tolist(),
                       "p10": env.p10.round(2).tolist(), "p90": env.p90.round(2).tolist()},
            "hourly": {"hour": hourly.index.tolist(), **{c: hourly[c].round(2).tolist() for c in cols}},
            "files": files_of(target, ("representative.csv", "envelope.csv", "daily.csv", "kpis.csv", "manifest.json",
                                       "semantics.ttl"))}


def lql_results(target, ind, lang):
    get = lambda k: ind.get(k) if isinstance(ind.get(k), (int, float)) else None  # noqa: E731
    phys, eqt, eqo = get("physical_dose_gy"), get("eqd_tumour_total"), get("eqd_oar_total")
    tcp, ntcp = get("tcp_percent"), get("ntcp_percent")
    analysis = T[lang]["lql_analysis"].format(
        phys=num(phys, ".1f", lang), eqt=num(eqt, ".1f", lang), eqo=num(eqo, ".1f", lang),
        days=num(get("overall_days_tumour"), ".0f", lang), tcp=num(tcp, ".0f", lang), ntcp=num(ntcp, ".0f", lang))
    kpis = [num(eqt, ".1f", lang), num(eqo, ".1f", lang), num(get("bed_tumour"), ".1f", lang),
            f"{num(ntcp, '.0f', lang)} / {num(tcp, '.0f', lang)}"]
    return {"kind": "lql", "kpis": kpis, "analysis": analysis, "qualification": qualification(target, "lql"),
            "bars": [phys, eqt, eqo], "probs": [tcp, ntcp],
            "files": files_of(target, ("indicators.csv", "manifest.json", "semantics.ttl"))}


def run(model, state, lang):
    out_root = Path(tempfile.mkdtemp(prefix="ws-"))
    try:
        target, ind = execute(to_scenario(state), DESC[model], WS, out_root)
        target = Path(target)
        return tls_results(target, state, lang) if model == "tls" else lql_results(target, ind, lang)
    finally:
        shutil.rmtree(out_root, ignore_errors=True)


def source_text(rec, lang):
    s = SOURCES[lang]
    if rec.get("origin") == "provided" and rec.get("evidence"):
        return s["provided"].format(rec["evidence"])
    kind = rec.get("kind")
    if kind == "convention":
        return s["convention"].format(rec.get("said", ""))
    if kind in ("default", "read"):
        return s[kind]
    return rec.get("source") or ""


def variables(state, lang):
    stated, accepted, proposed = T[lang]["status"]
    rows = []
    for group in ("inputs", "experiment"):
        for name, rec in state[group].items():
            status = stated if rec.get("origin") == "provided" else accepted if rec.get("accepted") else proposed
            rows.append([label(name, lang), shown(name, rec.get("value"), lang), "", status, source_text(rec, lang)])
    return rows


def clarify_text(model, state, verdict, lang):
    t = T[lang]
    short = lambda i: i["parameter"].split(".")[-1]  # noqa: E731
    waiting = [short(i) for i in verdict["issues"] if i["code"] == "unaccepted_assumption"]
    missing = [short(i) for i in verdict["issues"] if i["code"] == "missing"]
    other = [f"{label(short(i), lang)} ({i['message']})" for i in verdict["issues"]
             if i["code"] not in ("unaccepted_assumption", "missing")]
    rec_of = lambda n: state[group_of(model, n)][n]  # noqa: E731
    conv = [n for n in waiting if rec_of(n).get("kind") == "convention"]
    q = ("« ", " »") if lang == "fr" else ("“", "”")
    sep = " : " if lang == "fr" else ": "
    parts = []
    if missing:
        parts.append(t["needed"].format(", ".join(label(n, lang) for n in missing)))
    if conv:
        parts.append(t["conventions"].format("; ".join(
            f"**{label(n, lang)}{sep}{shown(n, rec_of(n)['value'], lang)}** ({q[0]}{rec_of(n).get('said', '')}{q[1]})"
            for n in conv)))
    if len(waiting) > len(conv):
        parts.append(t["defaults"].format(len(waiting) - len(conv)))
    if waiting:
        parts.append(t["pending"])
    if other:
        parts.append(t["fix"].format("; ".join(other)))
    return "\n\n".join(parts)

# ---------------------------------------------------------------- API used by the page (JSON in, JSON out)


def api_fresh(model, lang):
    return json.dumps(fresh(model, lang))


def api_needs_reading(message):
    """A pure confirmation is handled without the language model."""
    return json.dumps(not is_pure_confirmation(message.strip()))


def api_summary(state_json):
    state = json.loads(state_json)
    summary = {g: {n: {k: r.get(k) for k in ("value", "unit", "origin", "accepted")}
                   for n, r in state[g].items()} for g in ("inputs", "experiment")}
    # context only, so that "that means 1200 m" refers to the parameter left unresolved; values are never taken from it
    summary["unresolved"] = state.get("unresolved") or []
    summary["previous_message"] = ((state.get("request") or "").splitlines() or [""])[-1][:300]
    return json.dumps(summary, ensure_ascii=False)


def respond(model, lang, state, reply, results=None, decision=None):
    verdict = decision or check(model, state, lang)["decision"]
    return json.dumps({"state": state, "reply": reply.strip(), "decision": verdict,
                       "variables": variables(state, lang), "results": results}, ensure_ascii=False, default=str)


def compute(model, lang, state):
    if over_limit(model, state):
        return respond(model, lang, state, T[lang]["limit"].format(MAX_DAYS, MAX_RUNS, MAX_POINTS), decision="clarify")
    try:
        results = run(model, state, lang)
    except ValueError as exc:
        return respond(model, lang, state, T[lang]["failed_run"].format(exc), decision="clarify")
    return respond(model, lang, state, T[lang]["computed"], results=results, decision="execute")


def api_turn(model, lang, state_json, message, parsed_json):
    """One turn. parsed_json is the language model's reading ('' when not read or not needed)."""
    t = T[lang]
    state = json.loads(state_json)
    message = message.strip()

    if is_pure_confirmation(message):  # deterministic: accept what was shown, then run if the validator agrees
        if state.get("unresolved"):  # a request that could not be applied is never replaced by the old value
            return respond(model, lang, state, t["blocked"].format(names(state["unresolved"], lang)), decision="clarify")
        for g, n in pending(state):
            state[g][n]["accepted"] = True
        verdict = check(model, state, lang)
        if verdict["decision"] == "execute":
            return compute(model, lang, state)
        return respond(model, lang, state, clarify_text(model, state, verdict, lang))

    if not parsed_json:  # a composite message that could not be read: nothing changes
        return respond(model, lang, state, t["unread"])

    parsed = json.loads(parsed_json)
    state["request"] = (state["request"] + "\n" + message).strip()
    task = str(parsed.get("task") or "")
    if task == "unsupported":
        return respond(model, lang, state, t["refused"], decision="refuse")
    if task and task != SINGLE_TASK[model]:
        return respond(model, lang, state, t["not_here"], decision="clarify")

    errors = []
    old = json.loads(json.dumps(state))  # to report what this message changed
    values = [v if isinstance(v, dict) else {} for v in parsed.get("values") or []]
    fields = [str(v.get("field") or "") for v in values]
    twice = {f for f in fields if fields.count(f) > 1}
    errors += [ERRORS[lang]["twice"].format(label(f, lang)) for f in sorted(twice)]
    failed = set(twice)
    for v in values:
        if str(v.get("field") or "") in twice:
            continue  # two readings for one parameter: neither is used
        error = apply_value(model, state, v, message, lang)
        if error:
            errors.append(error)
            failed.add(str(v.get("field") or ""))
    q = ("« ", " »") if lang == "fr" else ("“", "”")
    sep = " : " if lang == "fr" else ": "
    named = named_fields(model, state, message)
    noted = []
    for g in ("inputs", "experiment"):
        for n, r in state[g].items():
            before = old[g].get(n)
            if r.get("origin") != "provided" or r == before:
                continue
            arrow = (f"{shown(n, before['value'], lang)} → " if before and before.get("value") is not None
                     and not same(before["value"], r["value"]) else "")
            how = f"{q[0]}{r['evidence']}{q[1]}" + (f"{sep}{r['relative']}" if r.get("relative") else "")
            warn = (t["not_named"] if before and (before.get("origin") == "provided" or before.get("accepted"))
                    and (g, n) not in named else "")
            noted.append(f"**{label(n, lang)}{sep}{arrow}{shown(n, r['value'], lang)}** ({how}){warn}")
    changed_fields = {n for g in ("inputs", "experiment") for n in state[g] if state[g][n] != old[g].get(n)}
    changed = bool(changed_fields)
    kept = bool(KEEP.search(message)) and bool(state.get("unresolved"))  # "keep": the current value stays
    kept_text = t["kept"].format(names(state["unresolved"], lang)) if kept else ""
    state["unresolved"] = sorted(failed | (set() if kept else set(state.get("unresolved") or []) - changed_fields))
    hold = bool(HOLD.search(message))
    restricted = bool(ONLY.search(message))
    if ACCEPT_WORD.search(message) and restricted and not hold:  # "yes, only for the length": named fields only
        chosen = [(g, n) for g, n in named_fields(model, state, message) if (g, n) in pending(state)]
        for g, n in chosen:
            state[g][n]["accepted"] = True
    else:
        chosen = []
    propose_defaults(model, state)
    verdict = check(model, state, lang)
    # the model's own sentences and questions are not shown: every statement and question in the reply comes from
    # this deterministic state, so the reply cannot contradict what was retained
    parts = [t["noted"].format("; ".join(noted))] if noted else []
    if kept_text:
        parts.append(kept_text)
    if not (changed or errors or chosen or kept):
        parts.append(t["unchanged"])
    if errors:
        parts.append(t["unused"].format("; ".join(errors)))
    if chosen:
        parts.append(t["accepted_some"].format(", ".join(label(n, lang) for _, n in chosen)))
    if hold:
        parts.append(t["held"])
    if verdict["decision"] == "refuse":
        parts.append(t["refused"])
    elif verdict["decision"] == "execute":
        if not state["unresolved"]:
            parts.append(t["ready"])  # a change or a question never runs the code in the same turn
    else:
        parts.append(clarify_text(model, state, verdict, lang))
    if state["unresolved"]:
        parts.append(t["blocked"].format(names(state["unresolved"], lang)))
    blocked = verdict["decision"] == "execute" or errors or state["unresolved"]
    decision = "clarify" if blocked and verdict["decision"] != "refuse" else verdict["decision"]
    return respond(model, lang, state, "\n\n".join(p for p in parts if p), decision=decision)


def api_example(model, lang):
    state = fresh(model, lang)
    base = json.loads((WS / "examples" / ("tls-complete.json" if model == "tls" else "lql-complete.json"))
                      .read_text(encoding="utf-8"))
    for group in ("inputs", "experiment"):
        for name, rec in base[group].items():
            state[group][name] = dict(rec, accepted=True, source="Example scenario (fictitious), stated and accepted")
    if model == "tls":
        state["experiment"]["n_days"]["value"], state["experiment"]["n_runs"]["value"] = 7, 5
    state["request"] = "Example scenario"
    out = json.loads(compute(model, lang, state))
    out["reply"] = T[lang]["example_done"]
    return json.dumps(out, ensure_ascii=False, default=str)
