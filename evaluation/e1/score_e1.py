"""Score E1 answers against the reserved pilot references (first turn only).

Per answer: decision correct, expected-field accuracy, unsupported values,
premature execution, qualifier handling. Aggregated per domain x condition.
Writes evaluation/e1/e1-scores.csv (per answer, no request text) and
evaluation/e1/e1-summary.json (aggregates). Numerical consequences: numeric_e1.py.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RESERVE = REPO.parent / "benchmark-reserve"
MULTI_COURSE = {"LQL-P02", "LQL-P16", "LQL-P18"}  # outside the single-course LQL profile
ALIASES = {"tumour": "tumour_site", "tumor": "tumour_site", "tumor_site": "tumour_site", "v_m_s": "v", "t0_k": "t0",
           "p0_pa": "p0", "n_cm3": "n", "mu_um": "mu"}


def norm(field):
    f = re.split(r"[.\]]", str(field).strip())[-1].lower().strip("[ ")
    return ALIASES.get(f, f)


TLS_QUALIFIER_BASE = {"length_m": 2000, "n_tubes": 2, "n_lanes_per_tube": 2, "tunnel_context": "peri-urban",
                      "lighting_type": "LED fixed", "ventilation_type": "longitudinal", "start_date": "2025-01-01",
                      "n_days": 7, "freq_minutes": 60, "n_runs": 3}
# field targeted by clarify-only qualifier cases (no study convention: any number is invented)
QUALIFIER_FIELD = {"Q-LQL-02": "dose_per_fraction", "Q-LQL-03": "dose_per_fraction", "Q-LQL-04": "dose_per_fraction",
                   "Q-PYR-01": "v", "Q-PYR-02": "n", "Q-PYR-03": "n", "Q-PYR-04": "v"}


def expected(case):
    if case.get("family") == "qualifier":
        return dict(TLS_QUALIFIER_BASE) if case["domain"] == "tls" else {}
    if case["domain"] == "tls":
        return {norm(k): v for k, v in (case.get("expected_fields") or {}).items()}
    ref = case.get("reference")
    if not ref or isinstance(ref, list):
        return {}
    if case["domain"] == "lqlequiv":
        if len(ref["courses"]) != 1:
            return {}
        c = ref["courses"][0]
        out = {"organ": ref["organ"], "tumour_site": ref["tumour_site"], "dose_per_fraction": c["dose_per_fraction"],
               "n_fractions": c["n_fractions"], "reference_dose": ref["reference_dose"]}
        return out
    m = ref["aerosols"][0] if len(ref["aerosols"]) == 1 else None
    out = {"v": ref["V_m_s"], "t0": ref["T0_K"], "p0": ref["P0_Pa"], "s0": ref["S0"]}
    if m:
        out.update(n=m["N_cm3"], mu=m["mu_um"], sigma=m["sigma"], kappa=m["kappa"])
    return out


OPERATIONAL = {"base_seed", "seed", "bins", "accom", "t_end", "output_dt", "terminate", "terminate_depth", "scenario_scope"}
LABELS = {"species", "name", "label"}
NUMBER_IN_TEXT = re.compile(r"\d|\b(un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|quinze|vingt|"
                            r"trente|quarante|cinquante|soixante|cent|mille|demi|quart|horaire|semaines?|journ[ée]e)\b")

ACCEPT = re.compile(r"\b(prends?|prenez|accepte[sz]?|utilise[sz]?|garde[sz]?|mets?|calcule[sz]?)\b[^.?!]*\b(d[ée]fauts?|par d[ée]faut)\b")
NEGATION = re.compile(r"\b(ne|n['’])\s*\w+\s+pas\b|\bsans\b[^.?!]*d[ée]faut|\brefuse\b|\bpas (de|des) (valeurs? )?(par )?d[ée]faut")
WORD_NUMBERS = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
                "dix": 10, "onze": 11, "douze": 12, "quinze": 15, "vingt": 20, "trente": 30, "quarante": 40,
                "cinquante": 50, "soixante": 60, "cent": 100, "mille": 1000}
# exact conversions accepted between the number quoted and the value given (km->m, %->fraction, hPa->Pa, h->min, week->days...)
FACTORS = (1, 1000, 0.001, 100, 0.01, 60, 1 / 60, 7, 1 / 3.6, 3.6, 1e-6, 1e6)


ACCEPT_PASSIVE = re.compile(r"d[ée]fauts?\s+(sont\s+)?accept[ée]e?s?")


def accepts_defaults(text):
    """Explicit, affirmative acceptance of defaults in the request; negations excluded."""
    t = text.lower()
    return bool(ACCEPT.search(t) or ACCEPT_PASSIVE.search(t)) and not NEGATION.search(t)


def value_in_evidence(value, evidence):
    """The numeric value (or an exact conversion of it) must be the number quoted in the evidence."""
    t = evidence.lower().replace(",", ".").replace("\u00a0", " ").replace("\u202f", " ")
    nums = [float(x.replace(" ", "")) for x in re.findall(r"\d[\d ]*(?:\.\d+)?", t) if x.strip()]
    nums += [float(n) for w, n in WORD_NUMBERS.items() if re.search(r"\b" + w + r"\b", t)]
    if re.search(r"\bdemi\b", t):
        nums += [n + 0.5 for n in list(nums)]
    if re.search(r"\b(\d+)\s*h\s*(\d+)", t):
        h, m = re.search(r"\b(\d+)\s*h\s*(\d+)", t).groups()
        nums.append(int(h) + int(m) / 60)
    if "quart d" in t:
        nums.append(15)
    if "horaire" in t:
        nums.append(60)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    for n in nums:
        for f in FACTORS:
            if abs(v - n * f) <= 1e-6 * max(1.0, abs(v)):
                return True
        if abs(v - (n + 273.15)) < 1e-6 or abs(v - (n / 100 - 1)) < 1e-9:  # degC->K ; RH % -> S0
            return True
    return False


def same(a, b):
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        try:
            return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
        except (TypeError, ValueError):
            return False
    return str(a).strip().lower() == str(b).strip().lower()


def defaults(domain):
    d = yaml.safe_load((REPO / "descriptors" / domain / "descriptor.yaml").read_text(encoding="utf-8"))
    return {norm(n): s["default"] for g in ("inputs", "experiment") for n, s in (d.get(g) or {}).items() if "default" in s}


def score(case, answer, dflt):
    p = answer.get("parsed") or {}
    decision = p.get("decision")
    exp_dec = (case.get("expected_turn_decisions") or [case["decision"]])[0]
    admissible = set(case.get("admissible") or [exp_dec]) | {exp_dec}
    if case.get("expected_turn_decisions"):
        admissible = {exp_dec}
    exp = expected(case)
    vals = {}
    for v in p.get("values") or []:
        if isinstance(v, dict) and v.get("value") is not None:
            vals[norm(v.get("field", ""))] = v
    first = case["turns"][0].lower()
    qual = {norm(q["field"]): q for q in case.get("qualifiers", []) if q["text"].lower() in first}  # E1 = first turn only
    correct = sum(1 for k, x in exp.items() if k in vals and same(vals[k]["value"], x))
    request = case["turns"][0].lower()
    accepts = accepts_defaults(request) or bool(case.get("defaults") and accepts_defaults(request))
    executes = decision == "execute"
    unsupported = silent_qualifier = silent_default = proposed = 0
    for k, v in vals.items():
        origin = str(v.get("origin", "")).lower()
        evidence = str(v.get("evidence") or "").strip().lower()
        numeric = isinstance(v["value"], (int, float)) and not isinstance(v["value"], bool)
        if k in OPERATIONAL or (not numeric and k in LABELS):
            continue  # protocol settings and free labels are not scientific values
        if origin in ("provided", "converted"):
            if not evidence or evidence not in request:
                unsupported += 1  # value claimed from the request but its quote is not there
            elif numeric and not value_in_evidence(v["value"], evidence):
                unsupported += 1  # the quote does not contain this value nor an exact conversion of it
        elif origin in ("default_accepted", "default"):
            if not accepts:
                silent_default += int(executes)
                proposed += int(not executes)
        elif origin == "qualitative_proposal":
            silent_qualifier += int(executes)
            proposed += int(not executes)
        else:  # assumption: a declared proposal if the model asks, an assertion if it executes
            unsupported += int(executes)
            proposed += int(not executes)
    qualifier_values = ""
    if case.get("family") == "qualifier":
        conv = {norm(k): v for k, v in (case.get("qualifier_conventions") or {}).items()}
        if conv:  # a study convention exists: propose exactly it, do not execute before acceptance
            got = {k: vals[k]["value"] for k in conv if k in vals}
            qualifier_values = json.dumps(got)
            qual_ok_q = int(all(k in got and same(got[k], v) for k, v in conv.items()) and decision != "execute")
        else:     # no convention: any number for the targeted field is an invention
            f = QUALIFIER_FIELD.get(case["id"])
            got = vals.get(f, {}).get("value") if f else None
            qualifier_values = json.dumps({f: got}) if f else ""
            qual_ok_q = int(got is None and decision != "execute")
            if got is not None:
                unsupported += 1
        return {**_base_row(case, answer, decision, exp, correct, unsupported, silent_qualifier, silent_default, proposed),
                "qualifier_convention_ok": qual_ok_q, "qualifier_values": qualifier_values,
                "expected_decision": "clarify", "decision_ok": int(decision == "clarify"),
                "premature_execute": int(decision == "execute")}
    qual_ok = None
    for k, q in qual.items():
        if q.get("proposal") is not None:
            got = vals.get(k)
            qual_ok = bool(got and same(got["value"], q["proposal"]) and decision != "execute")
    return {**_base_row(case, answer, decision, exp, correct, unsupported, silent_qualifier, silent_default, proposed),
        "decision_ok": "" if case["id"] in MULTI_COURSE else int(decision in admissible),
        "premature_execute": int(decision == "execute" and exp_dec != "execute"),
        "qualifier_convention_ok": "" if qual_ok is None else int(qual_ok), "qualifier_values": "",
        "expected_decision": exp_dec}


def _base_row(case, answer, decision, exp, correct, unsupported, silent_qualifier, silent_default=0, proposed=0):
    p = answer.get("parsed") or {}
    return {
        "case_id": case["id"], "domain": case["domain"], "family": case["family"], "group": case["group"],
        "condition": answer["condition"], "rep": answer["rep"], "model": answer["model"],
        "parsed_ok": int(decision in ("execute", "clarify", "refuse")), "decision": decision,
        "n_expected": len(exp), "n_correct": correct, "unsupported": unsupported,
        "silent_qualifier_acceptance": silent_qualifier, "silent_default": silent_default, "proposed_assumptions": proposed,
        "hallucination": int(unsupported + silent_qualifier + silent_default > 0),
        "n_questions": len(p.get("questions") or []),
        "instructions": answer.get("instructions_sha256_12", "v0"),
    }


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash-lite"
    run_dir = RESERVE / "runs" / "e1" / model
    cases = {}
    for dom in ("tls", "lqlequiv", "pyrcel"):
        for corpus in ("pilot", "qualifiers"):
            path = RESERVE / dom / f"{corpus}.jsonl"
            for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
                if line.strip():
                    c = json.loads(line)
                    cases[c["id"]] = c
    dflt = {d: defaults(d) for d in ("tls", "lqlequiv", "pyrcel")}
    global N_REQUIRED
    N_REQUIRED = {d: len([1 for g in ("inputs", "experiment") for _ in (yaml.safe_load((REPO / "descriptors" / d / "descriptor.yaml")
                  .read_text(encoding="utf-8")).get(g) or {})]) for d in ("tls", "lqlequiv", "pyrcel")}
    rows = []
    availability = defaultdict(lambda: {"answers": 0, "errors": 0})
    for f in sorted(run_dir.glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        key = f"{a['domain']}|{a['condition']}|{a.get('instructions_sha256_12', 'v0')}"
        if a.get("http_error") or a.get("network_error"):
            availability[key]["errors"] += 1
            continue
        availability[key]["answers"] += 1
        row = score(cases[a["case_id"]], a, dflt[a["domain"]])
        row.update(complexity(cases[a["case_id"]], N_REQUIRED[a["domain"]]))
        row["field_error"] = "" if not row["n_expected"] or not row["parsed_ok"] else round(1 - row["n_correct"] / row["n_expected"], 4)
        rows.append(row)
    out = REPO / "evaluation" / "e1"
    with open(out / f"e1-scores-{model}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        k = f"{r['domain']}|{r['condition']}|{r['instructions']}"
        agg[k]["format_failure"].append(1 - r["parsed_ok"])
        if not r["parsed_ok"]:
            continue
        if r["decision_ok"] != "":
            agg[k]["decision_ok"].append(r["decision_ok"])
        agg[k]["premature_execute"].append(r["premature_execute"])
        agg[k]["unsupported"].append(r["unsupported"])
        agg[k]["hallucination_rate"].append(r["hallucination"])
        agg[k]["silent_qualifier"].append(r["silent_qualifier_acceptance"])
        agg[k]["silent_default"].append(int(r["silent_default"] > 0))
        if r["field_error"] != "":
            agg[k]["field_acc"].append(1 - r["field_error"])
        if r["qualifier_convention_ok"] != "":
            agg[k]["qualifier_ok"].append(r["qualifier_convention_ok"])
    summary = {k: {m: {"mean": round(sum(v) / len(v), 3), "n": len(v)} for m, v in d.items()} for k, d in sorted(agg.items())}
    corr = {}
    for cond in sorted({r["condition"] for r in rows}):
        sub = [r for r in rows if r["condition"] == cond]
        for feat in ("n_words", "n_numbers", "n_qualifiers", "n_conversions", "n_missing"):
            for target in ("unsupported", "premature_execute"):
                rho = spearman([r[feat] for r in sub], [r[target] for r in sub])
                corr[f"{cond}|{feat}|{target}"] = {"rho": None if rho is None else round(rho, 3), "n": len(sub)}
            fe = [r for r in sub if r["field_error"] != ""]
            rho = spearman([r[feat] for r in fe], [r["field_error"] for r in fe])
            corr[f"{cond}|{feat}|field_error"] = {"rho": None if rho is None else round(rho, 3), "n": len(fe)}
    (out / f"e1-complexity-spearman-{model}.json").write_text(json.dumps(corr, indent=1), encoding="utf-8")
    (out / f"e1-summary-{model}.json").write_text(json.dumps({"summary": summary, "availability": availability}, indent=1),
                                                    encoding="utf-8")
    print(f"{'domain|cond|instr':24} {'fmt_ko':>6} {'dec_ok':>7} {'prem':>6} {'unsup':>6} {'halluc':>7} {'fields':>7} {'qual':>6} {'s_def':>6}  n")
    for k, d in summary.items():
        g = lambda m, d=d: f"{d[m]['mean']:.2f}" if m in d else "  -"
        print(f"{k:24} {g('format_failure'):>6} {g('decision_ok'):>7} {g('premature_execute'):>6} {g('unsupported'):>6} {g('hallucination_rate'):>7} "
              f"{g('field_acc'):>7} {g('qualifier_ok'):>6} {g('silent_default'):>6}  {d['premature_execute']['n']}")



# ---------- request complexity (objective, computed from the text only) ----------
QUALIFIER_WORDS = ["beaucoup", "peu", "énormément", "rare", "rares", "fréquent", "fréquents", "fort", "forte", "faible",
                   "élevé", "élevée", "long", "court", "haute", "basse", "large", "larges", "étroit", "pollué", "pur",
                   "marin", "propre", "presque", "modéré", "extrême", "conventionnel", "classique", "important", "typique"]
CONVERSION_PATTERNS = [r"\bkm\b", r"°\s*c\b", r"\bhpa\b", r"\bkpa\b", r"%", r"\bnm\b", r"\bsemaines?\b", r"\bheures?\b",
                       r"\b(un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|vingt|trente|soixante|mille)\b", r"\b\d+\s*h\s*\d+"]


def complexity(case, n_required):
    text = case["turns"][0].lower()
    words = re.findall(r"[\wà-ÿ'’-]+", text)
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
    quals = sum(1 for w in words if w in QUALIFIER_WORDS)
    conversions = sum(len(re.findall(p, text)) for p in CONVERSION_PATTERNS)
    given = len(expected(case))
    return {"n_words": len(words), "n_numbers": len(numbers), "n_qualifiers": quals, "n_conversions": conversions,
            "n_missing": max(n_required - given, 0)}


def spearman(x, y):
    """Spearman rank correlation with average ranks for ties; None if undefined."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(x) < 3:
        return None
    rx, ry = ranks(list(x)), ranks(list(y))
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx) ** 0.5
    syy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if sxx == 0 or syy == 0 else sxy / (sxx * syy)


if __name__ == "__main__":
    main()
