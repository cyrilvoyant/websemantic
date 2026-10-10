"""WebSemantic on Hugging Face: talk to scientific codes that ask before they compute (English / Français).

A language model (Mistral, free plan) reads each message against the code's contract and returns a structured
scenario (values with unit, origin and quoted evidence). Everything after that is local and deterministic, as in the
study: declared conventions and defaults are only proposed, acceptance must be explicit, the validator decides
(execute, clarify, refuse), and the unchanged, pinned code computes. Outputs come back with units, provenance and
validity limits. The same functions are MCP tools for the visitor's own AI assistant.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

REPO = "https://github.com/cyrilvoyant/websemantic"
TAG = "v0.2.6"
HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent if (HERE.parent / "descriptors").exists() else HERE / "workspace"  # inside the repository: use it
WS = Path(os.environ.get("WEBSEMANTIC_WORKSPACE", LOCAL)).resolve()
BACKENDS = ("external/LQL-Equiv-web", "external/tunnel-load-simulator")
MAX_DAYS, MAX_RUNS = 90, 20  # keeps the free CPU responsive for everyone


def bootstrap():
    """Fetch the pinned WebSemantic release and the two backends used here (pyrcel is too heavy for a free CPU)."""
    if not (WS / "descriptors").exists():
        subprocess.run(["git", "clone", "--depth", "1", "--branch", TAG, REPO, str(WS)], check=True)
        for sub in BACKENDS:
            subprocess.run(["git", "-C", str(WS), "submodule", "update", "--init", "--depth", "1", sub], check=True)
    sys.path.insert(0, str(WS / "src"))
    env = WS / ".env"  # local tests only (never committed); on the Space the key is a secret
    if not os.environ.get("MISTRAL_API_KEY") and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("MISTRAL_API_KEY="):
                os.environ["MISTRAL_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                os.environ.setdefault("MISTRAL_MODEL", "codestral-latest")  # the local key is a Codestral key


bootstrap()
from websemantic.core.validation import Parameter, Scenario, validate  # noqa: E402
from websemantic.registry import execute, load_descriptor  # noqa: E402
from websemantic.units import normalize, parse_number  # noqa: E402

MODEL_NAME = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
CODES = ("tls", "lql")
PACKS = {"tls": "tls", "lql": "lqlequiv"}
DESC = {m: load_descriptor(WS, m) for m in CODES}
CONTRACT = {m: (WS / "packs" / PACKS[m] / "LLM-CONTRACT.md").read_text(encoding="utf-8") for m in CODES}

T = {
    "en": {
        "codes": {"tls": "Road tunnel energy", "lql": "Radiotherapy dose"},
        "tagline": "ask before you compute",
        "intro": "Describe your case. The code asks for what is missing and computes only what you accept.",
        "note": "Fictitious scenarios only, no personal data · messages read by Mistral",
        "placeholder": "Describe your case… e.g. a long tunnel with a lot of traffic",
        "try": "Examples", "example_btn": "Example without language model", "reset_btn": "New conversation",
        "files": "Download outputs and provenance",
        "examples": {
            "tls": ["Electricity demand of a 2 km road tunnel, two tubes with two lanes each, fixed LED lighting, over 30 days.",
                    "A long tunnel with a lot of traffic, keep the rest as usual.",
                    "Give me the exact real consumption of the Mont-Blanc tunnel next year to certify its design."],
            "lql": ["Equivalent dose of 20 sessions of 3 Gy for the prostate, rectum as organ at risk.",
                    "Moderate hypofractionation in 20 sessions, prostate, rectum.",
                    "Should I treat my patient, Mr Martin, with 20 × 3 Gy?"]},
        "explain": {"missing": "no value yet", "unaccepted_assumption": "proposed, waiting for your agreement",
                    "unsupported_origin": "origin not allowed", "evidence": "quote not found in your message",
                    "unit": "not the canonical unit", "bounds": "outside the declared bounds",
                    "category": "not an allowed category", "type": "wrong type", "finite": "must be finite",
                    "unknown_field": "not a parameter of this code", "conflict": "conflicting values",
                    "unsupported_task": "outside what the code supports"},
        "computed": "All values are stated or accepted: the pinned code has run. Results, time series, analysis and "
                    "provenance are on the right.",
        "refused": "This request is outside what the code supports, so nothing is computed.",
        "needed": "Still needed: **{}**.",
        "conventions": "From your words I propose {} (declared conventions of the code).",
        "pending": "{} value(s) are proposals (see Variables). Reply **yes** to accept them, or give your own values. "
                   "Nothing is computed before that.",
        "fix": "To fix: {}.", "unused": "_Not used: {}._",
        "limit": "This free server simulates at most {} days and {} Monte Carlo runs: please reduce the period.",
        "llm_down": "I cannot reach the language service right now (the free quota may be used up). You can still run "
                    "the example below the chat, which needs no language model.",
        "example_done": "Example computed without the language model: every value is stated and accepted (see Variables).",
        "status": ("stated by you", "accepted", "proposed, to accept"),
        "decision": {"execute": "Computed with the pinned code", "clarify": "The code asks before computing",
                     "refuse": "Refused: outside what the code supports"},
        "period": "Default period on the free server (7 days, 5 runs); change it in the chat (up to 90 days, 20 runs)",
        "tls_analysis": "**Analysis.** Over {days} simulated days the median peak power is **{peak:,.0f} kW** and the mean "
                        "**{mean:,.0f} kW** (load factor {lf:.2f}); demand is highest around **{hour}:00**. Energy splits "
                        "into lighting {li:.0f} %, ventilation {ve:.0f} % and auxiliaries {au:.0f} %. Between Monte Carlo "
                        "runs the 10–90 % band is ±{band:.0f} % of the median on average. The annual figure ({ann:,.0f} "
                        "MWh/yr) extrapolates the period by 365/{days}; it is not a seasonally complete year.",
        "lql_analysis": "**Analysis.** A physical dose of {phys:.1f} Gy corresponds to an EQD2 of **{eqt:.1f} Gy** for the "
                        "target ({gain:+.0f} %) and **{eqo:.1f} Gy** for the organ at risk, over {days:.0f} days. The model "
                        "gives a tumour control probability of {tcp:.0f} % and a complication probability of {ntcp:.0f} %. "
                        "These are model outputs for a fictitious scenario with the parameters of the code's library; "
                        "they do not support any clinical decision.",
        "plots": {"power": "Power time series (kW)", "band": "10–90 % of Monte Carlo runs", "median": "median",
                  "daily": "Average daily profile by use (kW)", "hour": "hour", "uses": ("lighting", "ventilation", "auxiliary"),
                  "eqd": "Equivalent dose in 2 Gy fractions (Gy)", "bars": ("physical dose", "EQD2 target", "EQD2 organ at risk"),
                  "prob": "Model probabilities (fictitious scenario)", "tcp": "tumour control (TCP)", "ntcp": "complication risk (NTCP)"},
        "kpis_tls": ("annualised energy (MWh/yr)", "peak power (kW)", "load factor", "specific energy (kWh/m/yr)"),
        "kpis_lql": ("EQD2 target (Gy)", "EQD2 organ at risk (Gy)", "BED target (Gy)", "NTCP / TCP (%)"),
        "prov": ("Code", "Nature", "Uncertainty covered", "not covered"),
    },
    "fr": {
        "codes": {"tls": "Énergie d'un tunnel", "lql": "Dose en radiothérapie"},
        "tagline": "demander avant de calculer",
        "intro": "Décrivez votre cas. Le code demande ce qui manque et ne calcule que ce que vous acceptez.",
        "note": "Scénarios fictifs, aucune donnée personnelle · messages lus par Mistral",
        "placeholder": "Décrivez votre cas… par ex. un tunnel long avec beaucoup de trafic",
        "try": "Exemples", "example_btn": "Exemple sans modèle de langage", "reset_btn": "Nouvelle conversation",
        "files": "Télécharger les sorties et la provenance",
        "examples": {
            "tls": ["Demande électrique d'un tunnel routier de 2 km, deux tubes à deux voies, éclairage LED fixe, sur 30 jours.",
                    "Un tunnel long avec beaucoup de trafic, le reste comme d'habitude.",
                    "Donne-moi la consommation réelle exacte du tunnel du Mont-Blanc l'an prochain pour certifier son dimensionnement."],
            "lql": ["Dose équivalente de 20 séances de 3 Gy pour la prostate, rectum comme organe à risque.",
                    "Hypofractionnement modéré en 20 séances, prostate, rectum.",
                    "Dois-je traiter mon patient, M. Martin, avec 20 × 3 Gy ?"]},
        "explain": {"missing": "pas encore de valeur", "unaccepted_assumption": "proposé, en attente de votre accord",
                    "unsupported_origin": "origine non admise", "evidence": "citation absente de votre message",
                    "unit": "pas l'unité canonique", "bounds": "hors des bornes déclarées",
                    "category": "catégorie non admise", "type": "type incorrect", "finite": "doit être fini",
                    "unknown_field": "pas un paramètre de ce code", "conflict": "valeurs contradictoires",
                    "unsupported_task": "hors du périmètre du code"},
        "computed": "Toutes les valeurs sont données ou acceptées : le code figé a tourné. Résultats, séries temporelles, "
                    "analyse et provenance sont à droite.",
        "refused": "Cette demande sort du périmètre du code : rien n'est calculé.",
        "needed": "Il manque encore : **{}**.",
        "conventions": "D'après vos mots, je propose {} (conventions déclarées du code).",
        "pending": "{} valeur(s) sont des propositions (voir Variables). Répondez **oui** pour les accepter, ou donnez vos "
                   "propres valeurs. Rien n'est calculé avant.",
        "fix": "À corriger : {}.", "unused": "_Non utilisé : {}._",
        "limit": "Ce serveur gratuit simule au plus {} jours et {} tirages Monte Carlo : réduisez la période.",
        "llm_down": "Le service de langage est injoignable pour l'instant (quota gratuit peut-être épuisé). L'exemple sous "
                    "la conversation fonctionne sans modèle de langage.",
        "example_done": "Exemple calculé sans modèle de langage : toutes les valeurs sont données et acceptées (voir Variables).",
        "status": ("donné par vous", "accepté", "proposé, à accepter"),
        "decision": {"execute": "Calculé avec le code figé", "clarify": "Le code demande avant de calculer",
                     "refuse": "Refusé : hors du périmètre du code"},
        "period": "Période par défaut du serveur gratuit (7 jours, 5 tirages) ; modifiable dans la conversation "
                  "(jusqu'à 90 jours, 20 tirages)",
        "tls_analysis": "**Analyse.** Sur {days} jours simulés, la puissance de pointe médiane est **{peak:,.0f} kW** et la "
                        "moyenne **{mean:,.0f} kW** (facteur de charge {lf:.2f}) ; la demande culmine vers **{hour} h**. "
                        "L'énergie se répartit entre éclairage {li:.0f} %, ventilation {ve:.0f} % et auxiliaires {au:.0f} %. "
                        "Entre tirages Monte Carlo, la bande 10–90 % vaut ±{band:.0f} % de la médiane en moyenne. Le chiffre "
                        "annuel ({ann:,.0f} MWh/an) extrapole la période par 365/{days} ; ce n'est pas une année complète "
                        "avec ses saisons.",
        "lql_analysis": "**Analyse.** Une dose physique de {phys:.1f} Gy correspond à une EQD2 de **{eqt:.1f} Gy** pour la "
                        "cible ({gain:+.0f} %) et de **{eqo:.1f} Gy** pour l'organe à risque, sur {days:.0f} jours. Le modèle "
                        "donne une probabilité de contrôle tumoral de {tcp:.0f} % et de complication de {ntcp:.0f} %. Ce "
                        "sont des sorties de modèle pour un scénario fictif, avec les paramètres de la bibliothèque du "
                        "code ; elles ne fondent aucune décision clinique.",
        "plots": {"power": "Puissance au cours du temps (kW)", "band": "10–90 % des tirages Monte Carlo", "median": "médiane",
                  "daily": "Profil journalier moyen par usage (kW)", "hour": "heure", "uses": ("éclairage", "ventilation", "auxiliaires"),
                  "eqd": "Dose équivalente en fractions de 2 Gy (Gy)", "bars": ("dose physique", "EQD2 cible", "EQD2 organe à risque"),
                  "prob": "Probabilités du modèle (scénario fictif)", "tcp": "contrôle tumoral (TCP)", "ntcp": "complication (NTCP)"},
        "kpis_tls": ("énergie annualisée (MWh/an)", "puissance de pointe (kW)", "facteur de charge", "énergie spécifique (kWh/m/an)"),
        "kpis_lql": ("EQD2 cible (Gy)", "EQD2 organe à risque (Gy)", "BED cible (Gy)", "NTCP / TCP (%)"),
        "prov": ("Code", "Nature", "Incertitude couverte", "non couverte"),
    },
}
SYSTEM = """You help a user prepare a scenario for one scientific code. The contract is the only authority.
- Never invent a value. A value is either stated by the user (origin "provided", evidence = the exact words of the
  user, copied character for character), a declared qualitative convention (origin "convention": put the name of
  the declared level whose expressions mean the same as the user's words in "level", and quote the user's vague
  words as evidence), or a declared default (origin "default").
- Never accept anything for the user. Use the canonical units of the parameter list.
- If the request is outside the supported tasks (real measured data, certification, a decision for a named patient),
  set task to "unsupported".
Reply with one JSON object only:
{"task": "<one supported task or unsupported>",
 "values": [{"field": "<exact parameter name>", "value": <number or category>, "unit": "<unit or null>",
             "origin": "provided|convention|default", "level": "<declared level, conventions only>",
             "evidence": "<exact quote>"}],
 "questions": ["<at most two short questions about what is missing or ambiguous>"],
 "message": "<two friendly sentences in the user's language; never give a numerical result, the code computes it>"}
Return in values only what the NEW message states or qualifies."""

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
                                          source="Declared default of the code, proposed", accepted=False)


def apply_value(model, state, v, message):
    """One value read by the model, checked locally. Returns a note when it cannot be used."""
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
                       source=f"Declared convention of the code: '{evidence}' read as level '{label}' = {value}. "
                              "Proposed, to accept; not a measurement.")
        elif origin == "default":
            if spec.get("default") is None:
                return f"{name}"
            rec = dict(value=spec["default"], unit=spec.get("unit"), origin="default", evidence=None, accepted=False,
                       source="Declared default of the code, proposed")
        else:
            value, source = (parse_number(raw, spec["type"]) if spec.get("type") in ("int", "float") else (raw, None))
            value, unit, conv = normalize(value, unit, evidence, spec)
            source = "; ".join(s for s in (source, conv) if s) or None
            if evidence and evidence in message:
                rec = dict(value=value, unit=unit, origin="provided", evidence=evidence, source=source, accepted=False)
            else:
                rec = dict(value=value, unit=unit, origin="assumption", evidence=None, accepted=False,
                           source="Read by the language model from your message (no exact quote); please confirm")
    except (ValueError, TypeError) as exc:
        return f"{name}: {exc}"
    state[group][name] = rec
    return None


CONSENT = re.compile(r"\b(yes|ok|okay|agree|accept|accepted|go ahead|confirm|fine|sure|sounds good|do it|"
                     r"oui|d'accord|j'accepte|j’accepte|vas-y|valide|je valide|c'est bon)\b", re.I)
NEGATION = re.compile(r"\b(no|not|don't|dont|never|non|pas|refuse)\b", re.I)


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

# ---------------------------------------------------------------- language model and speech


def ask_model(model, state, message, lang):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("no key")
    desc = DESC[model]
    params = [{"field": n, "type": s.get("type"), "unit": s.get("unit"), "default": s.get("default"),
               "label": s.get("label"), "categories": s.get("categories"),
               "declared_levels": {lab: {"value": val, "expressions": (s.get("qualitative_scale") or {})
                                         .get("levels", {}).get(lab, {}).get("aliases", [])}
                                   for val, lab in declared_levels(s).items()} or None}
              for g in ("inputs", "experiment") for n, s in (desc.get(g) or {}).items()]
    current = {g: {n: {k: r.get(k) for k in ("value", "unit", "origin", "accepted")} for n, r in state[g].items()}
               for g in ("inputs", "experiment")}
    prompt = (f"SUPPORTED TASKS: {json.dumps(desc['tasks']['supported'], ensure_ascii=False)}\n"
              f"CONTRACT:\n{CONTRACT[model]}\nPARAMETERS:\n{json.dumps(params, ensure_ascii=False)}\n"
              f"CURRENT SCENARIO:\n{json.dumps(current, ensure_ascii=False)}\n"
              f"REPLY LANGUAGE for message and questions: {'French' if lang == 'fr' else 'English'}\n"
              f"NEW MESSAGE:\n{message}")
    host = "codestral.mistral.ai" if MODEL_NAME.startswith("codestral") else "api.mistral.ai"
    payload = {"model": MODEL_NAME, "temperature": 0, "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request(f"https://{host}/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.load(r)
    return json.loads(raw["choices"][0]["message"]["content"])


_WHISPER = None


def transcribe(path):
    global _WHISPER
    if not path:
        return ""
    if _WHISPER is None:
        from faster_whisper import WhisperModel
        _WHISPER = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = _WHISPER.transcribe(path, beam_size=1, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()

# ---------------------------------------------------------------- results


def run(model, state):
    verdict = check(model, state)
    if verdict["decision"] != "execute":
        return verdict, None, None
    target, indicators = execute(to_scenario(state), DESC[model], WS, Path(tempfile.mkdtemp(prefix="ws-")))
    return verdict, Path(target), indicators


def qualification(target):
    m = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    sw = m.get("software", {})
    return {"software": {k: sw.get(k) for k in ("name", "version", "repository", "commit", "doi", "licence")},
            "nature": m.get("nature"), "uncertainty": m.get("uncertainty"), "validity_notes": m.get("validity_notes"),
            "note": m.get("note")}


INK, MID, LIGHT = "#1f2a37", "#6b7280", "#c7ccd3"  # sober palette: one dark ink, two greys
PLOT = dict(template="simple_white", height=290, margin=dict(l=50, r=10, t=36, b=60),
            font=dict(family="Inter, Helvetica, Arial, sans-serif", size=12, color=INK),
            legend=dict(orientation="h", yanchor="top", y=-0.18, x=0, font=dict(size=11)))


def layout(fig, title, **kw):
    fig.update_layout(**{**PLOT, **kw}, title=dict(text=title, x=0, xanchor="left", font=dict(size=13)))


def localise(text, lang):
    """French typography for numbers: 4,732 -> 4 732 and 0.59 -> 0,59 (English unchanged)."""
    if lang != "fr":
        return text
    return re.sub(r"\d[\d,]*\.?\d*", lambda m: m.group(0).replace(",", "\u202f").replace(".", ","), text)


def kpi_html(labels, values):
    cells = "".join(f"<div class='ws-kpi'><div class='ws-kpi-v'>{v}</div><div class='ws-kpi-l'>{lab}</div></div>"
                    for lab, v in zip(labels, values))
    return f"<div class='ws-kpis'>{cells}</div>"


def tls_results(target, state, lang):
    t, p = T[lang], T[lang]["plots"]
    env = pd.read_csv(target / "envelope.csv", parse_dates=["timestamp"])
    rep = pd.read_csv(target / "representative.csv", parse_dates=["timestamp"])
    k = pd.read_csv(target / "kpis.csv").median(numeric_only=True)
    f1 = go.Figure([
        go.Scatter(x=env.timestamp, y=env.p90, line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=env.timestamp, y=env.p10, fill="tonexty", fillcolor="rgba(107,114,128,0.18)", line=dict(width=0),
                   name=p["band"]),
        go.Scatter(x=env.timestamp, y=env["median"], line=dict(color=INK, width=1.4), name=p["median"])])
    layout(f1, p["power"], yaxis_title="kW")
    cols = ("lighting_kw", "ventilation_kw", "auxiliary_kw")
    hourly = rep.groupby(rep.timestamp.dt.hour)[list(cols)].mean()
    f2 = go.Figure([go.Bar(x=hourly.index, y=hourly[c], name=n, marker_color=col)
                    for c, n, col in zip(cols, p["uses"], (INK, MID, LIGHT))])
    layout(f2, p["daily"], barmode="stack", xaxis_title=p["hour"], yaxis_title="kW")
    shares = [rep[c].sum() for c in cols]
    days = state["experiment"].get("n_days", {}).get("value")
    analysis = localise(t["tls_analysis"].format(
        days=days, peak=k.peak_kw, mean=k.mean_kw, lf=k.load_factor, hour=int(hourly.sum(axis=1).idxmax()),
        li=100 * shares[0] / sum(shares), ve=100 * shares[1] / sum(shares), au=100 * shares[2] / sum(shares),
        band=float(((env.p90 - env.p10) / env["median"]).mean() * 50), ann=k.annualized_mwh), lang)
    kp = localise(kpi_html(t["kpis_tls"], (f"{k.annualized_mwh:,.0f}", f"{k.peak_kw:,.0f}", f"{k.load_factor:.2f}",
                                           f"{k.specific_kwh_m_year:,.0f}")), lang)
    files = [str(target / f) for f in ("representative.csv", "envelope.csv", "daily.csv", "kpis.csv", "manifest.json")
             if (target / f).exists()]
    return kp, f1, f2, analysis, files


def lql_results(target, ind, lang):
    t, p = T[lang], T[lang]["plots"]
    vals = (ind["physical_dose_gy"], ind["eqd_tumour_total"], ind["eqd_oar_total"])
    f1 = go.Figure(go.Bar(x=list(p["bars"]), y=list(vals), marker_color=[LIGHT, INK, MID],
                          text=[f"{v:.1f} Gy" for v in vals], textposition="outside"))
    layout(f1, p["eqd"], yaxis_title="Gy")
    probs = (ind["tcp_percent"], ind["ntcp_percent"])
    f2 = go.Figure(go.Bar(y=[p["tcp"], p["ntcp"]], x=list(probs), orientation="h", marker_color=[INK, MID],
                          text=[f"{v:.0f} %" for v in probs], textposition="outside"))
    layout(f2, p["prob"], height=210, xaxis=dict(range=[0, 110], title="%"))
    analysis = localise(t["lql_analysis"].format(phys=vals[0], eqt=vals[1], eqo=vals[2],
                                                 gain=100 * (vals[1] / vals[0] - 1), days=ind["overall_days_tumour"],
                                                 tcp=ind["tcp_percent"], ntcp=ind["ntcp_percent"]), lang)
    kp = localise(kpi_html(t["kpis_lql"], (f"{vals[1]:.1f}", f"{vals[2]:.1f}", f"{ind['bed_tumour']:.1f}",
                                           f"{ind['ntcp_percent']:.0f} / {ind['tcp_percent']:.0f}")), lang)
    files = [str(target / f) for f in ("indicators.csv", "manifest.json") if (target / f).exists()]
    return kp, f1, f2, analysis, files


def provenance_md(target, lang):
    labels = T[lang]["prov"]
    q = qualification(target)
    sw, unc = q["software"], q.get("uncertainty") or {}
    lines = [f"**{labels[0]}:** {sw.get('name')} {sw.get('version') or ''} · commit `{(sw.get('commit') or '')[:7]}` · "
             f"DOI [{sw.get('doi')}](https://doi.org/{sw.get('doi')}) · {sw.get('licence')}",
             f"**{labels[1]}:** {q.get('nature') or q.get('note')}"]
    if unc:
        lines.append(f"**{labels[2]}:** " + ", ".join(unc.get("covered", [])) + f" · **{labels[3]}:** "
                     + ", ".join(unc.get("not_covered", [])))
    lines += [f"- {n}" for n in q.get("validity_notes") or []]
    return "\n\n".join(lines)


def variables_table(state, lang):
    stated, accepted, proposed = T[lang]["status"]
    rows = []
    for group in ("inputs", "experiment"):
        for name, rec in state[group].items():
            status = stated if rec.get("origin") == "provided" else accepted if rec.get("accepted") else proposed
            rows.append([name, rec.get("value"), (rec.get("unit") or "").replace("unit:", ""), status,
                         rec.get("source") or (f"“{rec.get('evidence')}”" if rec.get("evidence") else "")])
    return pd.DataFrame(rows, columns=["parameter", "value", "unit", "status", "source"])


def decision_html(verdict, lang):
    rule = {"execute": "#1f2a37", "clarify": "#8a6d3b", "refuse": "#8b2c2c"}[verdict["decision"]]
    return (f"<div class='ws-decision' style='border-left-color:{rule}'><span class='ws-code'>"
            f"{verdict['decision']}</span> {T[lang]['decision'][verdict['decision']]}</div>")

# ---------------------------------------------------------------- MCP tools


def list_models() -> str:
    """List the scientific codes that WebSemantic can run here.

    Returns:
        JSON list of {id, definition, supported_tasks}. Use the id in the other tools.
    """
    return json.dumps([{"id": m, "definition": T["en"]["codes"][m], "supported_tasks": DESC[m]["tasks"]["supported"]}
                       for m in CODES], ensure_ascii=False, indent=1)


def get_contract(model: str) -> str:
    """Return the readable contract of a code: rules, parameters with units and bounds, conventions for vague words,
    and the cases where you must ask the user. Read it before building a scenario.

    Args:
        model: "tls" (road-tunnel electricity demand) or "lql" (radiotherapy dose equivalence).
    """
    return CONTRACT[model]


def validate_scenario(model: str, scenario_json: str) -> str:
    """Check a scenario before any calculation. Returns "execute", "clarify" or "refuse" with the reasons.
    On "clarify", ask the user; never fill a value yourself.

    Args:
        model: "tls" or "lql".
        scenario_json: JSON object with request, task, inputs and experiment; each parameter has value, unit
            (canonical unit of the contract), origin ("provided" with an exact evidence quote from the request, or
            "assumption" / "default" with a source), evidence, source and accepted (true only after the user agreed).
    """
    return json.dumps(check(model, json.loads(scenario_json)), ensure_ascii=False, indent=1)


def run_scenario(model: str, scenario_json: str) -> str:
    """Run the pinned scientific code on a scenario that passes validation and return qualified outputs: indicators
    with units, exact software revision and DOI, nature of the results and validity limits. If the scenario does not
    pass validation, nothing runs and the reasons are returned.

    Args:
        model: "tls" or "lql".
        scenario_json: the same JSON as for validate_scenario, after the user accepted every proposal.
    """
    state = json.loads(scenario_json)
    if over_limit(model, state):
        return json.dumps({"decision": "clarify", "issues": [{"parameter": "experiment",
                                                              "message": T["en"]["limit"].format(MAX_DAYS, MAX_RUNS)}]})
    verdict, target, indicators = run(model, state)
    if target is None:
        return json.dumps(verdict, ensure_ascii=False, indent=1)
    return json.dumps({"decision": "execute", "indicators": indicators, "qualification": qualification(target)},
                      ensure_ascii=False, indent=1, default=float)

# ---------------------------------------------------------------- conversation


def converse(message, history, state, model, lang):
    """One turn: returns the history, the state and the right-hand panels."""
    t = T[lang]
    history = list(history or [])
    message = (message or "").strip()
    if not message:
        return history, state, *([gr.skip()] * 7)
    history.append({"role": "user", "content": message})
    if consents(message):
        accept_all(state)  # acceptance covers what was proposed before this message, never what it adds
    state["request"] = (state["request"] + "\n" + message).strip()
    notes, questions = [], []
    try:
        parsed = ask_model(model, state, message, lang)
        if parsed.get("task") == "unsupported":
            state["task"] = "unsupported request"
        for v in parsed.get("values") or []:
            note = apply_value(model, state, v, message)
            if note:
                notes.append(note)
        questions = [q for q in parsed.get("questions") or [] if isinstance(q, str)][:2]
        reply = str(parsed.get("message") or "").strip()
    except (RuntimeError, urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        reply = t["llm_down"]
    propose_defaults(model, state)
    verdict = check(model, state, lang)
    outputs = [gr.skip()] * 5
    if verdict["decision"] == "execute" and over_limit(model, state):
        verdict = {"decision": "clarify", "issues": []}
        reply += "\n\n" + t["limit"].format(MAX_DAYS, MAX_RUNS)
    elif verdict["decision"] == "execute":
        _, target, ind = run(model, state)
        kp, f1, f2, analysis, files = tls_results(target, state, lang) if model == "tls" else lql_results(target, ind, lang)
        outputs = [kp, f1, f2, analysis + "\n\n" + provenance_md(target, lang), files]
        reply += "\n\n" + t["computed"]
    elif verdict["decision"] == "refuse":
        reply += "\n\n" + t["refused"]
    else:
        short = lambda i: i["parameter"].split(".")[-1]  # noqa: E731
        pending = [short(i) for i in verdict["issues"] if i["code"] == "unaccepted_assumption"]
        missing = [short(i) for i in verdict["issues"] if i["code"] == "missing"]
        other = [f"{short(i)} ({i['message']})" for i in verdict["issues"]
                 if i["code"] not in ("unaccepted_assumption", "missing")]
        conv = [n for n in pending if "convention" in (state[group_of(model, n)][n].get("source") or "")]
        if missing:
            reply += "\n\n" + t["needed"].format(", ".join(missing))
        if questions:
            reply += "\n\n" + " ".join(questions)
        if conv:
            reply += "\n\n" + t["conventions"].format(
                "; ".join(f"**{n} = {state[group_of(model, n)][n]['value']}**" for n in conv))
        if pending:
            reply += "\n\n" + t["pending"].format(len(pending))
        if other:
            reply += "\n\n" + t["fix"].format("; ".join(other))
    if notes:
        reply += "\n\n" + t["unused"].format("; ".join(notes))
    history.append({"role": "assistant", "content": reply.strip()})
    return history, state, decision_html(verdict, lang), variables_table(state, lang), *outputs


def example_without_llm(model, lang):
    """Deterministic: a fully stated example, computed without any language model."""
    state = fresh(model, lang)
    base = json.loads((WS / "examples" / ("tls-complete.json" if model == "tls" else "lql-complete.json"))
                      .read_text(encoding="utf-8"))
    for group in ("inputs", "experiment"):
        for name, rec in base[group].items():
            state[group][name] = dict(rec, accepted=True, source="Example scenario (fictitious), stated and accepted")
    if model == "tls":
        state["experiment"]["n_days"]["value"], state["experiment"]["n_runs"]["value"] = 7, 5
    state["request"] = "Example scenario"
    _, target, ind = run(model, state)
    kp, f1, f2, analysis, files = tls_results(target, state, lang) if model == "tls" else lql_results(target, ind, lang)
    history = [{"role": "assistant", "content": T[lang]["example_done"]}]
    return (history, state, decision_html(check(model, state, lang), lang), variables_table(state, lang), kp, f1, f2,
            analysis + "\n\n" + provenance_md(target, lang), files)

# ---------------------------------------------------------------- page


LOGO = WS / "docs" / "logo.png"
LOGO_B64 = base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


def header(lang):
    t = T[lang]
    return f"<div class='ws-head'><h1>WebSemantic <span>{t['tagline']}</span></h1><p>{t['intro']}</p></div>"


def footer(lang):
    return (f"<p class='ws-links'>{T[lang]['note']} · <a href='{REPO}'>GitHub</a> · "
            "<a href='https://doi.org/10.5281/zenodo.23238902'>DOI</a> · "
            "<a href='https://pypi.org/project/websemantic/'>PyPI</a> · MIT</p>")


CSS = """
.gradio-container{max-width:1380px !important}
.ws-head{margin:2px 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px}
.ws-head h1{margin:0;font-size:24px;font-weight:600;color:#1f2a37;letter-spacing:-.01em}
.ws-head h1 span{font-weight:400;color:#6b7280;font-size:17px;margin-left:8px}
.ws-head p{margin:4px 0;max-width:1050px;font-size:14px;color:#374151}
.ws-links,.ws-links a{color:#9ca3af !important;font-size:12px;text-align:center;margin-top:6px}
.ws-decision{border-left:3px solid;padding:4px 10px;font-size:14px;color:#1f2a37}
.ws-code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;text-transform:uppercase;
  letter-spacing:.05em;color:#6b7280;margin-right:6px}
.ws-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border-top:1px solid #e5e7eb;
  border-bottom:1px solid #e5e7eb;margin:6px 0}
.ws-kpi{padding:8px 10px}
.ws-kpi+.ws-kpi{border-left:1px solid #e5e7eb}
.ws-kpi-v{font-size:20px;font-weight:600;color:#1f2a37}
.ws-kpi-l{font-size:11.5px;color:#6b7280}
@media (max-width: 760px){
  .gradio-container{padding:6px !important}
  .ws-head h1{font-size:20px}
  .ws-head h1 span{display:block;margin:2px 0 0;font-size:15px}
  .ws-head p{font-size:13px}
  #ws-chat{height:52vh !important;min-height:300px}
  .ws-kpis{grid-template-columns:1fr 1fr}
  .ws-kpi:nth-child(3){border-left:none}
  .ws-kpi:nth-child(n+3){border-top:1px solid #e5e7eb}
}
"""
THEME = gr.themes.Base(primary_hue=gr.themes.colors.slate, secondary_hue=gr.themes.colors.slate,
                       neutral_hue=gr.themes.colors.gray, radius_size=gr.themes.sizes.radius_sm,
                       font=[gr.themes.GoogleFont("Inter"), "Helvetica", "Arial", "sans-serif"]).set(
    body_background_fill="#ffffff", block_shadow="none", block_border_width="1px",
    button_primary_background_fill="#1f2a37", button_primary_background_fill_hover="#374151",
    button_primary_text_color="#ffffff", button_secondary_background_fill="#ffffff")
MCP_URL = "https://cyrilvoyant-websemantic.hf.space/gradio_api/mcp/sse"

with gr.Blocks(title="WebSemantic — ask before you compute", theme=THEME, css=CSS) as demo:
    head = gr.HTML(header("en"))
    with gr.Row():
        lang = gr.Radio([("English", "en"), ("Français", "fr")], value="en", show_label=False, container=False, scale=1)
        model = gr.Radio([(T["en"]["codes"][m], m) for m in CODES], value="tls", show_label=False, container=False, scale=3)
    state = gr.State(fresh("tls"))
    with gr.Row(equal_height=False):
        with gr.Column(scale=5, min_width=340):
            chat = gr.Chatbot(type="messages", height=470, show_label=False, elem_id="ws-chat")
            with gr.Row():
                text = gr.Textbox(placeholder=T["en"]["placeholder"], show_label=False, scale=6, submit_btn=True)
                mic = gr.Audio(sources=["microphone"], type="filepath", show_label=False, scale=2,
                               waveform_options=gr.WaveformOptions(show_recording_waveform=False))
            examples = gr.Dataset(components=[text], samples=[[e] for e in T["en"]["examples"]["tls"]], label=T["en"]["try"])
            with gr.Row():
                b_example = gr.Button(T["en"]["example_btn"], size="sm")
                b_reset = gr.Button(T["en"]["reset_btn"], size="sm")
        with gr.Column(scale=6, min_width=340):
            decision = gr.HTML()
            with gr.Tabs():
                with gr.Tab("Results · Résultats"):
                    kpis = gr.HTML()
                    fig1 = gr.Plot(show_label=False)
                    fig2 = gr.Plot(show_label=False)
                    analysis = gr.Markdown()
                    files = gr.File(label=T["en"]["files"], file_count="multiple")
                with gr.Tab("Variables"):
                    variables = gr.Dataframe(wrap=True, interactive=False, show_label=False)
                with gr.Tab("MCP"):
                    gr.Markdown(f"""**EN.** This page is also an **MCP server**. Add it as a connector in an assistant that
supports remote MCP servers (connector or MCP settings of the assistant).
**FR.** Cette page est aussi un **serveur MCP** : ajoutez-la comme connecteur dans votre assistant.

`{MCP_URL}`

Tools / outils : `list_models`, `get_contract`, `validate_scenario`, `run_scenario`.""")
                with gr.Tab("About · À propos"):
                    gr.Markdown(f"""Each code has one **descriptor** (parameters, units, bounds, defaults with their source,
outputs, conventions for vague words), compiled into a **contract** for language models, an **ontology with SHACL
rules** and **FAIR metadata**. The language model only reads your message against the contract; a local
**validator** decides, and the **unchanged, pinned code** computes. In a benchmark of 72 requests and three models,
adding the contract reduced premature execution from 26 to 6 %, 17 to 1 % and 52 to 23 %.

Source [{REPO}]({REPO}) (release {TAG}) · [DOI](https://doi.org/10.5281/zenodo.23238902) ·
[w3id ontology](https://w3id.org/websemantic/ns) · FOOPS! 1.0 · howfairis 5/5 · OpenSSF best practices: passing.""")

    foot = gr.HTML(footer("en"))
    panels = [decision, variables, kpis, fig1, fig2, analysis, files]

    def reset(m, lg):
        t = T[lg]
        return ([], fresh(m, lg), "", pd.DataFrame(), "", None, None, "", None,
                gr.Dataset(samples=[[e] for e in t["examples"][m]], label=t["try"]), header(lg),
                gr.Radio(choices=[(t["codes"][c], c) for c in CODES], value=m), gr.Textbox(placeholder=t["placeholder"]),
                gr.Button(t["example_btn"]), gr.Button(t["reset_btn"]), gr.File(label=t["files"]), footer(lg))

    resets = [chat, state, *panels, examples, head, model, text, b_example, b_reset, files, foot]

    def from_voice(path, history, st, m, lg):
        said = transcribe(path)
        return (said, *converse(said, history, st, m, lg)) if said else ("", history, st, *([gr.skip()] * 7))

    text.submit(converse, [text, chat, state, model, lang], [chat, state, *panels], api_name=False).then(
        lambda: "", None, text, api_name=False)
    mic.stop_recording(from_voice, [mic, chat, state, model, lang], [text, chat, state, *panels], api_name=False).then(
        lambda: (None, ""), None, [mic, text], api_name=False)
    examples.click(lambda s: s[0], examples, text, api_name=False)
    b_example.click(example_without_llm, [model, lang], [chat, state, *panels], api_name=False)
    b_reset.click(reset, [model, lang], resets, api_name=False)
    model.input(reset, [model, lang], resets, api_name=False)
    lang.input(reset, [model, lang], resets, api_name=False)
    gr.api(list_models, api_name="list_models")
    gr.api(get_contract, api_name="get_contract")
    gr.api(validate_scenario, api_name="validate_scenario")
    gr.api(run_scenario, api_name="run_scenario")

if __name__ == "__main__":
    demo.launch(mcp_server=True)
