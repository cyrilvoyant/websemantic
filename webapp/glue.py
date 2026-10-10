"""WebSemantic in the browser (Pyodide): the deterministic half of each conversation turn.

The relay sends the visitor's message and the contract to the language model and returns its JSON reading. Here,
locally and unchanged from the study: declared conventions and defaults are only proposed, acceptance must be
explicit, the validator decides (execute, clarify, refuse), and the pinned codes compute (sha256-checked sources).
"""

import json
import re
import tempfile
from pathlib import Path

import pandas as pd

from websemantic.core.validation import Parameter, Scenario, validate
from websemantic.registry import execute, load_descriptor
from websemantic.units import normalize, parse_number

WS = Path("/home/pyodide/ws")
CODES = ("tls", "lql")
DESC = {m: load_descriptor(WS, m) for m in CODES}
MAX_DAYS, MAX_RUNS = 60, 10  # keeps the visitor's browser responsive

T = {
    "en": {
        "explain": {"missing": "no value yet", "unaccepted_assumption": "proposed, waiting for your agreement",
                    "unsupported_origin": "origin not allowed", "evidence": "quote not found in your message",
                    "unit": "not the canonical unit", "bounds": "outside the declared bounds",
                    "category": "not an allowed category", "type": "wrong type", "finite": "must be finite",
                    "unknown_field": "not a parameter of this code", "conflict": "conflicting values",
                    "unsupported_task": "outside what the code supports"},
        "computed": "All values are stated or accepted: the pinned code has run. Results are on the right.",
        "refused": "This request is outside what the code supports, so nothing is computed.",
        "needed": "Still needed: **{}**.",
        "conventions": "From your words I propose {}.",
        "defaults": "The other {} parameters take the code's default values (see Variables).",
        "pending": "Reply **yes** to accept, or give your own values. Nothing is computed before that.",
        "fix": "To fix: {}.", "unused": "_Not used: {}._",
        "limit": "In the browser, simulations are limited to {} days and {} Monte Carlo runs: please reduce the period.",
        "llm_down": "The language service is busy or unavailable right now. Try again in a moment, or run the example.",
        "example_done": "Example computed without the language model: every value is stated and accepted (see Variables).",
        "status": ("stated by you", "accepted", "proposed, to accept"),
        "period": "Default period in the browser (7 days, 5 runs); change it in the chat (up to 60 days, 10 runs)",
        "tls_analysis": "Over {days} simulated days the median peak power is {peak:,.0f} kW and the mean {mean:,.0f} kW "
                        "(load factor {lf:.2f}); demand is highest around {hour}:00. Energy splits into lighting "
                        "{li:.0f} %, ventilation {ve:.0f} % and auxiliaries {au:.0f} %. Between Monte Carlo runs the "
                        "10–90 % band is ±{band:.0f} % of the median on average. The annual figure ({ann:,.0f} MWh/yr) "
                        "extrapolates the period by 365/{days}; it is not a seasonally complete year.",
        "lql_analysis": "A physical dose of {phys:.1f} Gy corresponds to an EQD2 of {eqt:.1f} Gy for the target "
                        "({gain:+.0f} %) and {eqo:.1f} Gy for the organ at risk, over {days:.0f} days. The model gives a "
                        "tumour control probability of {tcp:.0f} % and a complication probability of {ntcp:.0f} %. "
                        "These are model outputs for a fictitious scenario with the parameters of the code's library; "
                        "they do not support any clinical decision.",
    },
    "fr": {
        "explain": {"missing": "pas encore de valeur", "unaccepted_assumption": "proposé, en attente de votre accord",
                    "unsupported_origin": "origine non admise", "evidence": "citation absente de votre message",
                    "unit": "pas l'unité canonique", "bounds": "hors des bornes déclarées",
                    "category": "catégorie non admise", "type": "type incorrect", "finite": "doit être fini",
                    "unknown_field": "pas un paramètre de ce code", "conflict": "valeurs contradictoires",
                    "unsupported_task": "hors du périmètre du code"},
        "computed": "Toutes les valeurs sont données ou acceptées : le code figé a tourné. Les résultats sont à droite.",
        "refused": "Cette demande sort du périmètre du code : rien n'est calculé.",
        "needed": "Il manque encore : **{}**.",
        "conventions": "D'après vos mots, je propose {}.",
        "defaults": "Les {} autres paramètres reprennent les valeurs par défaut du code (voir Variables).",
        "pending": "Répondez **oui** pour accepter, ou donnez vos propres valeurs. Rien n'est calculé avant.",
        "fix": "À corriger : {}.", "unused": "_Non utilisé : {}._",
        "limit": "Dans le navigateur, les simulations sont limitées à {} jours et {} tirages Monte Carlo : réduisez la période.",
        "llm_down": "Le service de langage est occupé ou indisponible. Réessayez dans un instant, ou lancez l'exemple.",
        "example_done": "Exemple calculé sans modèle de langage : toutes les valeurs sont données et acceptées (voir Variables).",
        "status": ("donné par vous", "accepté", "proposé, à accepter"),
        "period": "Période par défaut dans le navigateur (7 jours, 5 tirages) ; modifiable dans la conversation "
                  "(jusqu'à 60 jours, 10 tirages)",
        "tls_analysis": "Sur {days} jours simulés, la puissance de pointe médiane est {peak:,.0f} kW et la moyenne "
                        "{mean:,.0f} kW (facteur de charge {lf:.2f}) ; la demande culmine vers {hour} h. L'énergie se "
                        "répartit entre éclairage {li:.0f} %, ventilation {ve:.0f} % et auxiliaires {au:.0f} %. Entre "
                        "tirages Monte Carlo, la bande 10–90 % vaut ±{band:.0f} % de la médiane en moyenne. Le chiffre "
                        "annuel ({ann:,.0f} MWh/an) extrapole la période par 365/{days} ; ce n'est pas une année complète.",
        "lql_analysis": "Une dose physique de {phys:.1f} Gy correspond à une EQD2 de {eqt:.1f} Gy pour la cible "
                        "({gain:+.0f} %) et de {eqo:.1f} Gy pour l'organe à risque, sur {days:.0f} jours. Le modèle donne "
                        "une probabilité de contrôle tumoral de {tcp:.0f} % et de complication de {ntcp:.0f} %. Ce sont "
                        "des sorties de modèle pour un scénario fictif, avec les paramètres de la bibliothèque du code ; "
                        "elles ne fondent aucune décision clinique.",
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
UNIT_FR = {"days": "jours", "× reference": "× référence"}


def localise(text, lang):
    if lang != "fr":
        return text
    return re.sub(r"\d[\d,]*\.?\d*", lambda m: m.group(0).replace(",", "\u00a0").replace(".", ","), text)


def label(name, lang):
    en, fr, _ = LABELS.get(name, (name, name, ""))
    return fr if lang == "fr" else en


def shown(name, value, lang):
    """A value as a person reads it: 9 000 m, 1,5 × référence, Rectum."""
    unit = LABELS.get(name, ("", "", ""))[2]
    unit = UNIT_FR.get(unit, unit) if lang == "fr" else unit
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = f"{value:,}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
    return localise(f"{text} {unit}".strip(), lang)

# ---------------------------------------------------------------- scenario state


def fresh(model, lang="en"):
    desc = DESC[model]
    state = {"request": "", "task": desc["tasks"]["supported"][0], "inputs": {}, "experiment": {}}
    for group in ("inputs", "experiment"):
        for name, spec in (desc.get(group) or {}).items():
            if spec.get("operational_default") and "default" in spec:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default",
                                          evidence=None, source=spec.get("operational_default_source"), accepted=True)
    if model == "tls":
        for name, value in (("n_days", 7), ("n_runs", 5)):
            state["experiment"][name] = dict(value=value, unit=desc["experiment"][name].get("unit"), origin="default",
                                             evidence=None, source=T[lang]["period"], accepted=False)
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
    for label, level in (scale.get("levels") or {}).items():
        value = level["value"] if "value" in level else scale.get("reference_upper", 0) * level.get("fraction", 0)
        out[int(value) if spec.get("type") == "int" else float(value)] = label
    return out


def propose_defaults(model, state):
    for group in ("inputs", "experiment"):
        for name, spec in (DESC[model].get(group) or {}).items():
            if name not in state[group] and spec.get("default") is not None:
                state[group][name] = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None,
                                          source="Declared default of the code, proposed", accepted=False, kind="default")


def apply_value(model, state, v, message):
    name = str(v.get("field") or "").split(".")[-1]
    group = group_of(model, name)
    if group is None:
        return f"'{name}'"
    spec = DESC[model][group][name]
    origin, evidence, raw, unit = v.get("origin"), str(v.get("evidence") or ""), v.get("value"), v.get("unit")
    old = state[group].get(name)
    if old and (old.get("origin") == "provided" or old.get("accepted")) and not (evidence and evidence in message):
        return None  # a later message that does not state this value never overrides it
    try:
        if origin == "convention":
            levels = {label: value for value, label in declared_levels(spec).items()}
            label = str(v.get("level") or "")
            if label not in levels:
                return f"{name} ('{label}')"
            value = levels[label]
            rec = dict(value=value, unit=spec.get("unit"), origin="assumption", evidence=None, accepted=False,
                       said=evidence, kind="convention",
                       source=f"Declared convention of the code: '{evidence}' read as level '{label}' = {value}. "
                              "Proposed, to accept; not a measurement.")
        elif origin == "default":
            if spec.get("default") is None:
                return name
            rec = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None, accepted=False,
                       kind="default", source="Declared default of the code, proposed")
        else:
            value, source = (parse_number(raw, spec["type"]) if spec.get("type") in ("int", "float") else (raw, None))
            value, unit, conv = normalize(value, unit, evidence, spec)
            source = "; ".join(s for s in (source, conv) if s) or None
            if evidence and evidence in message:
                rec = dict(value=value, unit=unit, origin="provided", evidence=evidence, source=source, accepted=False)
            else:
                rec = dict(value=value, unit=unit, origin="assumption", evidence=None, accepted=False, kind="read",
                           source="Read by the language model from your message (no exact quote); please confirm")
    except (ValueError, TypeError) as exc:
        return f"{name}: {exc}"
    state[group][name] = rec
    return None


CONSENT = re.compile(r"\b(yes|ok|okay|agree|accept|accepted|go ahead|confirm|fine|sure|sounds good|do it|"
                     r"oui|d'accord|j'accepte|j’accepte|vas-y|valide|je valide|c'est bon)\b", re.IGNORECASE)
NEGATION = re.compile(r"\b(no|not|don't|dont|never|non|pas|refuse)\b", re.IGNORECASE)


def consents(message):
    return bool(CONSENT.search(message)) and not NEGATION.search(message) and "?" not in message


def accept_all(state):
    for group in ("inputs", "experiment"):
        for rec in state[group].values():
            if rec.get("origin") in ("assumption", "default") and rec.get("source") and rec.get("value") is not None:
                rec["accepted"] = True


def over_limit(model, state):
    if model != "tls":
        return False
    exp = state["experiment"]
    return (exp.get("n_days", {}).get("value") or 0) > MAX_DAYS or (exp.get("n_runs", {}).get("value") or 0) > MAX_RUNS

# ---------------------------------------------------------------- results


def qualification(target):
    m = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    sw = m.get("software", {})
    return {"software": {k: sw.get(k) for k in ("name", "version", "repository", "commit", "doi", "licence")},
            "nature": m.get("nature"), "uncertainty": m.get("uncertainty") or {},
            "validity_notes": m.get("validity_notes") or [], "note": m.get("note"),
            "verification": m.get("source_verification")}


def files_of(target, names):
    return {n: (target / n).read_text(encoding="utf-8") for n in names if (target / n).exists()}


def tls_results(target, state, lang):
    env = pd.read_csv(target / "envelope.csv")
    rep = pd.read_csv(target / "representative.csv", parse_dates=["timestamp"])
    k = pd.read_csv(target / "kpis.csv").median(numeric_only=True)
    cols = ("lighting_kw", "ventilation_kw", "auxiliary_kw")
    hourly = rep.groupby(rep.timestamp.dt.hour)[list(cols)].mean()
    shares = [rep[c].sum() for c in cols]
    days = state["experiment"].get("n_days", {}).get("value")
    analysis = localise(T[lang]["tls_analysis"].format(
        days=days, peak=k.peak_kw, mean=k.mean_kw, lf=k.load_factor, hour=int(hourly.sum(axis=1).idxmax()),
        li=100 * shares[0] / sum(shares), ve=100 * shares[1] / sum(shares), au=100 * shares[2] / sum(shares),
        band=float(((env.p90 - env.p10) / env["median"]).mean() * 50), ann=k.annualized_mwh), lang)
    kpis = [localise(f"{k.annualized_mwh:,.0f}", lang), localise(f"{k.peak_kw:,.0f}", lang),
            localise(f"{k.load_factor:.2f}", lang), localise(f"{k.specific_kwh_m_year:,.0f}", lang)]
    return {"kind": "tls", "kpis": kpis, "analysis": analysis, "qualification": qualification(target),
            "series": {"t": env.timestamp.tolist(), "median": env["median"].round(2).tolist(),
                       "p10": env.p10.round(2).tolist(), "p90": env.p90.round(2).tolist()},
            "hourly": {"hour": hourly.index.tolist(), **{c: hourly[c].round(2).tolist() for c in cols}},
            "files": files_of(target, ("representative.csv", "envelope.csv", "daily.csv", "kpis.csv", "manifest.json"))}


def lql_results(target, ind, lang):
    vals = (ind["physical_dose_gy"], ind["eqd_tumour_total"], ind["eqd_oar_total"])
    analysis = localise(T[lang]["lql_analysis"].format(
        phys=vals[0], eqt=vals[1], eqo=vals[2], gain=100 * (vals[1] / vals[0] - 1), days=ind["overall_days_tumour"],
        tcp=ind["tcp_percent"], ntcp=ind["ntcp_percent"]), lang)
    kpis = [localise(f"{vals[1]:.1f}", lang), localise(f"{vals[2]:.1f}", lang),
            localise(f"{ind['bed_tumour']:.1f}", lang), f"{ind['ntcp_percent']:.0f} / {ind['tcp_percent']:.0f}"]
    return {"kind": "lql", "kpis": kpis, "analysis": analysis, "qualification": qualification(target),
            "bars": [round(v, 2) for v in vals], "probs": [round(ind["tcp_percent"], 1), round(ind["ntcp_percent"], 1)],
            "files": files_of(target, ("indicators.csv", "manifest.json"))}


def run(model, state, lang):
    target, ind = execute(to_scenario(state), DESC[model], WS, Path(tempfile.mkdtemp(prefix="ws-")))
    target = Path(target)
    return tls_results(target, state, lang) if model == "tls" else lql_results(target, ind, lang)


SOURCES = {"en": {"provided": "your words: “{}”", "convention": "declared convention of the code for “{}”",
                   "default": "declared default of the code", "read": "read by the language model, to confirm"},
           "fr": {"provided": "vos mots : « {} »", "convention": "convention déclarée du code pour « {} »",
                   "default": "valeur par défaut du code", "read": "lu par le modèle de langage, à confirmer"}}


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

# ---------------------------------------------------------------- API used by the page (JSON in, JSON out)


def api_fresh(model, lang):
    return json.dumps(fresh(model, lang))


def api_summary(state_json):
    """What the relay sends to the language model: current values only (small, no sources)."""
    state = json.loads(state_json)
    return json.dumps({g: {n: {k: r.get(k) for k in ("value", "unit", "origin", "accepted")}
                           for n, r in state[g].items()} for g in ("inputs", "experiment")}, ensure_ascii=False)


def api_turn(model, lang, state_json, message, parsed_json):
    """One turn after the language model answered (parsed_json = '' when it could not be reached)."""
    t = T[lang]
    state = json.loads(state_json)
    message = message.strip()
    if consents(message):
        accept_all(state)  # acceptance covers what was proposed before this message, never what it adds
    state["request"] = (state["request"] + "\n" + message).strip()
    notes, questions, reply = [], [], ""
    if parsed_json:
        parsed = json.loads(parsed_json)
        if parsed.get("task") == "unsupported":
            state["task"] = "unsupported request"
        for v in parsed.get("values") or []:
            note = apply_value(model, state, v, message)
            if note:
                notes.append(note)
        questions = [q for q in parsed.get("questions") or [] if isinstance(q, str)][:2]
        reply = str(parsed.get("message") or "").strip()
    else:
        reply = t["llm_down"]
    propose_defaults(model, state)
    verdict = check(model, state, lang)
    results = None
    if verdict["decision"] == "execute" and over_limit(model, state):
        verdict = {"decision": "clarify", "issues": []}
        reply += "\n\n" + t["limit"].format(MAX_DAYS, MAX_RUNS)
    elif verdict["decision"] == "execute":
        results = run(model, state, lang)
        reply = t["computed"]  # the model's sentence may still ask for agreement; the code has the last word
    elif verdict["decision"] == "refuse":
        reply += "\n\n" + t["refused"]
    else:
        short = lambda i: i["parameter"].split(".")[-1]  # noqa: E731
        pending = [short(i) for i in verdict["issues"] if i["code"] == "unaccepted_assumption"]
        missing = [short(i) for i in verdict["issues"] if i["code"] == "missing"]
        other = [f"{label(short(i), lang)} ({i['message']})" for i in verdict["issues"]
                 if i["code"] not in ("unaccepted_assumption", "missing")]
        rec_of = lambda n: state[group_of(model, n)][n]  # noqa: E731
        conv = [n for n in pending if rec_of(n).get("kind") == "convention"]
        quotes = ("« ", " »") if lang == "fr" else ("“", "”")
        if missing:
            reply += "\n\n" + t["needed"].format(", ".join(label(n, lang) for n in missing))
            if questions:
                reply += "\n\n" + " ".join(questions)
        if conv:
            reply += "\n\n" + t["conventions"].format("; ".join(
                f"**{label(n, lang)} : {shown(n, rec_of(n)['value'], lang)}** ({quotes[0]}{rec_of(n).get('said', '')}{quotes[1]})"
                if lang == "fr" else
                f"**{label(n, lang)}: {shown(n, rec_of(n)['value'], lang)}** ({quotes[0]}{rec_of(n).get('said', '')}{quotes[1]})"
                for n in conv))
        others = len(pending) - len(conv)
        if others:
            reply += "\n\n" + t["defaults"].format(others)
        if pending:
            reply += "\n\n" + t["pending"]
        if other:
            reply += "\n\n" + t["fix"].format("; ".join(other))
    return json.dumps({"state": state, "notes": notes, "reply": reply.strip(), "decision": verdict["decision"],
                       "variables": variables(state, lang), "results": results}, ensure_ascii=False, default=str)


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
    return json.dumps({"state": state, "reply": T[lang]["example_done"], "decision": check(model, state, lang)["decision"],
                       "variables": variables(state, lang), "results": run(model, state, lang)},
                      ensure_ascii=False, default=str)
