"""Numerical consequence of the first answers (plan: evaluation/PREREG-numeric-consequence.md).

inventory  freeze the list of main-campaign answers (F000, F010; 3 models; 3 repetitions; 60 pilot requests) with SHA-256
run        categorise every answer of the numeric set and recompute the comparable ones with the pinned codes
summary    coverage table, per-request errors of the primary outputs, paired contrast F000 - F010 per code
Usage: python numeric_consequence.py inventory | run [--limit N] | summary   (pyrcel and TLS need their pinned sources)
"""

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numeric_e1 as N  # noqa: E402  (same comparison and replay functions as the earlier numeric check)

HERE = Path(__file__).resolve().parent
RUNS = {"mistral-small": "local_mistral-small-3.2-24b__20261008T085744Z-full",
        "qwen": "local_qwen2.5-72b__20261008T085744Z-full",
        "codestral": "codestral-latest__final-20261008"}
CONDITIONS = ("F000", "F010")
DOMAINS = ("tls", "lqlequiv", "pyrcel")
PRIMARY = {"tls": "total_mwh", "lqlequiv": "eqd_oar_total", "pyrcel": "Nd"}
# numeric_e1 returns pyrcel's native Nd in m^-3; the adapter reports cm^-3 (output.Nd / 1e6): converted here, unit stated.
SCALE = {"tls": 1.0, "lqlequiv": 1.0, "pyrcel": 1e-6}
UNIT = {"tls": "MWh", "lqlequiv": "Gy", "pyrcel": "cm^-3"}
CONFIGS = {"tls": N.tls_configs, "lqlequiv": N.lql_configs, "pyrcel": N.pyrcel_configs}
INVENTORY = HERE / "numeric-consequence-inventory.csv"
ANSWERS = HERE / "numeric-consequence-answers.csv"
SECONDARY = HERE / "numeric-consequence-secondary.csv"
REFERENCES = HERE / "numeric-consequence-references.csv"
SUMMARY = HERE / "numeric-consequence-summary.json"


def cases():
    out = {}
    for d in DOMAINS:
        for line in (N.RESERVE / d / "pilot.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                out[c["id"]] = c
    return out


def admissible(case):
    return set(case.get("admissible") or [case.get("decision")])


def numeric_set(case):
    """Execute admissible, reference from the first turn only, single aerosol mode for pyrcel."""
    if "execute" not in admissible(case) or not N.expected(case):
        return False
    if case.get("variants") or case.get("modifications") or case.get("expected_turn_decisions"):
        return False
    if case["domain"] == "tls" and not case.get("reference_scenarios"):
        return False
    if case["domain"] == "pyrcel" and not all(k in N.expected(case) for k in N.PYR_MODE):
        return False
    return True


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    rows = []
    for model, folder in RUNS.items():
        for cid in sorted(cases()):
            for cond in CONDITIONS:
                for rep in (1, 2, 3):
                    f = N.RESERVE / "runs" / "e1" / folder / f"{cid}_{cond}_r{rep}.json"
                    rows.append({"model": model, "condition": cond, "case_id": cid, "rep": rep,
                                 "file": f.relative_to(N.RESERVE).as_posix(), "sha256": sha256(f) if f.exists() else "missing"})
    with INVENTORY.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "answers,", sum(r["sha256"] == "missing" for r in rows), "missing ->", INVENTORY.name)


def categorise(case, answer):
    parsed = answer.get("parsed") or {}
    decision = parsed.get("decision")
    if decision not in ("execute", "clarify", "refuse"):
        return "unparsed", ""
    if decision != "execute":
        return ("justified_abstention" if decision in admissible(case) else "unjustified_abstention"), decision
    if not N.complete(case, answer):
        missing = sorted(k for k in N.expected(case) if k not in N.llm_values(answer))
        return "incomplete_configuration", " ".join(missing)
    issue = N.candidate_issue(answer, case)
    if issue:
        return "invalid_configuration", issue
    return None, ""


def run(limit=None):
    frozen = list(csv.DictReader(INVENTORY.open(encoding="utf-8")))
    cs = cases()
    answers, secondary, references, cache = [], [], [], {}
    selected = [r for r in frozen if numeric_set(cs[r["case_id"]])]
    for i, r in enumerate(selected[:limit] if limit else selected, 1):
        case = cs[r["case_id"]]
        domain = case["domain"]
        head = {k: r[k] for k in ("model", "condition", "case_id", "rep")} | {"domain": domain, "primary": PRIMARY[domain],
                                                                              "unit": UNIT[domain]}
        f = N.RESERVE / r["file"]
        if r["sha256"] == "missing" or not f.exists():
            answers.append({**head, "category": "technical_failure", "detail": "answer file missing"})
            continue
        assert sha256(f) == r["sha256"], f"answer changed since the inventory: {r['file']}"
        answer = json.loads(f.read_text(encoding="utf-8"))
        category, detail = categorise(case, answer)
        if category:
            answers.append({**head, "category": category, "detail": detail})
            continue
        ref_cfg, got_cfg, replay = CONFIGS[domain](case, answer)
        key = json.dumps(ref_cfg, sort_keys=True, default=str)
        if key not in cache:
            try:
                first, second = replay(ref_cfg), replay(ref_cfg)  # second run: numerical reproducibility
                a, b = (x["scalars"][PRIMARY[domain]] * SCALE[domain] for x in (first, second))
                references.append({"case_id": case["id"], "domain": domain, "primary": PRIMARY[domain], "unit": UNIT[domain],
                                   "run1": a, "run2": b, "difference": abs(a - b)})
                cache[key] = first
            except Exception as exc:  # noqa: BLE001 - a reference failure is a technical failure, not a candidate error
                cache[key] = exc
        if isinstance(cache[key], Exception):
            answers.append({**head, "category": "technical_failure", "detail": f"reference: {type(cache[key]).__name__}"})
            continue
        try:
            got = replay(got_cfg)
        except Exception as exc:  # noqa: BLE001 - the code rejected the candidate configuration
            answers.append({**head, "category": "invalid_configuration", "detail": f"rejected by the code: {type(exc).__name__}"})
            continue
        rows = N.compare(cache[key], got)
        secondary += [{**head, **row} for row in rows]
        completed = sorted(k for k in (ref_cfg if isinstance(ref_cfg, dict) else {})
                           if k not in N.llm_values(answer) and not k.startswith("_"))
        primary = next(row for row in rows if row["quantity"] == PRIMARY[domain])
        if primary["status"] == "period_differs":
            answers.append({**head, "category": "different_support", "detail": "period or time step differs"})
            continue
        if primary["status"] != "ok":
            answers.append({**head, "category": "technical_failure", "detail": primary["status"]})
            continue
        ref_value, got_value = (x["scalars"][PRIMARY[domain]] * SCALE[domain] for x in (cache[key], got))
        answers.append({**head, "category": "comparable_with_completion" if completed else "comparable_without_completion",
                        "detail": " ".join(completed), "reference": ref_value, "value": got_value,
                        "abs_err": primary["abs_err"] * SCALE[domain], "rel_err": primary["rel_err"]})
        if i % 25 == 0:
            print(i, "answers")
    for path, rows in ((ANSWERS, answers), (SECONDARY, secondary), (REFERENCES, references)):
        keys = list(dict.fromkeys(k for row in rows for k in row)) or ["empty"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
    print(len(answers), "answers ->", ANSWERS.name, "|", dict(Counter(a["category"] for a in answers)))


def holm(pvalues):
    order = sorted(pvalues, key=pvalues.get)
    adjusted, running = {}, 0.0
    for rank, name in enumerate(order):
        running = max(running, min(1.0, (len(order) - rank) * pvalues[name]))
        adjusted[name] = running
    return adjusted


def summary():
    from scipy.stats import wilcoxon

    rows = list(csv.DictReader(ANSWERS.open(encoding="utf-8")))
    out = {"coverage": {}, "per_code": {}, "per_model": {}}
    for d in DOMAINS:
        for cond in CONDITIONS:
            out["coverage"][f"{d}|{cond}"] = dict(Counter(r["category"] for r in rows if r["domain"] == d and r["condition"] == cond))
    comparable = [r for r in rows if r["category"].startswith("comparable")]
    errors = defaultdict(list)
    for r in comparable:
        errors[(r["domain"], r["case_id"], r["condition"])].append(float(r["abs_err"]))
        out["per_model"].setdefault(f"{r['domain']}|{r['model']}|{r['condition']}", []).append(float(r["abs_err"]))
    out["per_model"] = {k: {"n": len(v), "median_abs_err": statistics.median(v)} for k, v in out["per_model"].items()}
    pvalues = {}
    for d in DOMAINS:
        requests = sorted({cid for (dd, cid, _) in errors if dd == d})
        med = {(cid, c): statistics.median(errors[(d, cid, c)]) for cid in requests for c in CONDITIONS if errors.get((d, cid, c))}
        paired = [cid for cid in requests if (cid, "F000") in med and (cid, "F010") in med]
        diffs = [med[(cid, "F000")] - med[(cid, "F010")] for cid in paired]
        nonzero = [x for x in diffs if x != 0]
        entry = {"primary": PRIMARY[d], "requests_with_comparable_answers": len(requests), "paired_requests": len(paired),
                 "median_abs_err_F000": statistics.median([med[(c, "F000")] for c in paired]) if paired else None,
                 "median_abs_err_F010": statistics.median([med[(c, "F010")] for c in paired]) if paired else None,
                 "differences_F000_minus_F010": dict(zip(paired, diffs)), "nonzero_differences": len(nonzero),
                 "ties": len(diffs) - len(nonzero), "lower_error_with_contract": sum(x > 0 for x in nonzero),
                 "higher_error_with_contract": sum(x < 0 for x in nonzero)}
        if len(nonzero) >= 6:
            entry["wilcoxon_p"] = float(wilcoxon(nonzero).pvalue)
            pvalues[d] = entry["wilcoxon_p"]
        else:
            entry["wilcoxon_p"] = "not tested (fewer than six non-zero differences)"
        out["per_code"][d] = entry
    for d, p in holm(pvalues).items():
        out["per_code"][d]["wilcoxon_p_holm"] = p
    SUMMARY.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["per_code"], indent=1, ensure_ascii=False))
    print(json.dumps(out["coverage"], indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("inventory", "run", "summary"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    {"inventory": inventory, "run": lambda: run(args.limit), "summary": summary}[args.mode]()
