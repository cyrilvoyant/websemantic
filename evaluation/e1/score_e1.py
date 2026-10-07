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


def expected(case):
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
    accepts_defaults = bool(case.get("defaults"))
    correct = sum(1 for k, x in exp.items() if k in vals and same(vals[k]["value"], x))
    unsupported = 0
    silent_qualifier = 0
    for k, v in vals.items():
        if k in exp:
            continue
        if k in qual or any(k.endswith(q) for q in qual):
            if decision == "execute" and qual.get(k, {}).get("requires_acceptance"):
                silent_qualifier += 1
            continue
        if accepts_defaults and k in dflt and same(v["value"], dflt[k]):
            continue
        if k in ("base_seed", "seed"):  # operational setting authorised by policy
            continue
        unsupported += 1
    qual_ok = None
    for k, q in qual.items():
        if q.get("proposal") is not None:
            got = vals.get(k)
            qual_ok = bool(got and same(got["value"], q["proposal"]) and decision != "execute")
    return {
        "case_id": case["id"], "domain": case["domain"], "family": case["family"], "group": case["group"],
        "condition": answer["condition"], "rep": answer["rep"], "model": answer["model"],
        "parsed_ok": int(decision in ("execute", "clarify", "refuse")), "decision": decision, "expected_decision": exp_dec,
        "decision_ok": "" if case["id"] in MULTI_COURSE else int(decision in admissible),
        "premature_execute": int(decision == "execute" and exp_dec != "execute"),
        "n_expected": len(exp), "n_correct": correct, "unsupported": unsupported,
        "silent_qualifier_acceptance": silent_qualifier, "qualifier_convention_ok": "" if qual_ok is None else int(qual_ok),
        "n_questions": len(p.get("questions") or []),
    }


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash-lite"
    run_dir = RESERVE / "runs" / "e1" / model
    cases = {}
    for dom in ("tls", "lqlequiv", "pyrcel"):
        for line in (RESERVE / dom / "pilot.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                cases[c["id"]] = c
    dflt = {d: defaults(d) for d in ("tls", "lqlequiv", "pyrcel")}
    global N_REQUIRED
    N_REQUIRED = {d: len([1 for g in ("inputs", "experiment") for _ in (yaml.safe_load((REPO / "descriptors" / d / "descriptor.yaml")
                  .read_text(encoding="utf-8")).get(g) or {})]) for d in ("tls", "lqlequiv", "pyrcel")}
    rows = []
    for f in sorted(run_dir.glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("http_error") or a.get("network_error"):
            continue
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
        k = f"{r['domain']}|{r['condition']}"
        agg[k]["format_failure"].append(1 - r["parsed_ok"])
        if not r["parsed_ok"]:
            continue
        if r["decision_ok"] != "":
            agg[k]["decision_ok"].append(r["decision_ok"])
        agg[k]["premature_execute"].append(r["premature_execute"])
        agg[k]["unsupported"].append(r["unsupported"])
        agg[k]["any_unsupported"].append(int(r["unsupported"] > 0))
        agg[k]["silent_qualifier"].append(r["silent_qualifier_acceptance"])
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
    (out / f"e1-summary-{model}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"{'domain|cond':16} {'fmt_ko':>6} {'dec_ok':>7} {'prem':>6} {'unsup':>6} {'any_uns':>7} {'fields':>7} {'qual':>6}  n")
    for k, d in summary.items():
        g = lambda m, d=d: f"{d[m]['mean']:.2f}" if m in d else "  -"  # noqa: E731
        print(f"{k:16} {g('format_failure'):>6} {g('decision_ok'):>7} {g('premature_execute'):>6} {g('unsupported'):>6} {g('any_unsupported'):>7} "
              f"{g('field_acc'):>7} {g('qualifier_ok'):>6}  {d['premature_execute']['n']}")



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
