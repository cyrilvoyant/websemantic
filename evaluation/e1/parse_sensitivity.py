"""Sensitivity of the simple contrast F000 -> F010 to unparseable answers (audit, 10 October 2026).

The scorer counts an unparseable answer as a format failure with premature_execute = 0 and decision_ok = 0 (primary,
unchanged). Here the same contrast is recomputed twice per model: all answers (primary) and parseable answers only
(parsed_ok = 1; a condition whose repetitions are all unparseable is dropped for that request). Unit: unique first-turn
request, repetitions averaged; complete blocks (as request_level.py) for finished campaigns, requests answered in all
eight conditions for a running campaign (as partial_rep.py). Wilcoxon signed-rank, zero differences discarded.
Descriptive; no correction. Output (private): e1-parse-sensitivity.csv.
Usage: python parse_sensitivity.py <folder>[:available] [...]
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from request_level import first_turns, units  # noqa: E402

CONDS = [f"F{i:03b}" for i in range(8)]
METRICS = ("premature_execute", "qualifier_convention_ok", "decision_ok")


def grouped_available(rows, turns):
    by = defaultdict(list)
    for r in rows:
        by[(r["domain"], turns[r["case_id"]])].append(r)
    return {k: rs for k, rs in by.items() if {r["condition"] for r in rs} == set(CONDS)}


def contrast(groups, metric, parsed_only):
    diffs, f0 = [], []
    for rs in groups.values():
        means = {}
        for c in ("F000", "F010"):
            v = [float(r[metric]) for r in rs if r["condition"] == c and r[metric] not in ("", None)
                 and (not parsed_only or r["parsed_ok"] == "1")]
            if v:
                means[c] = sum(v) / len(v)
        if len(means) == 2:
            diffs.append(means["F010"] - means["F000"])
            f0.append(means["F000"])
    if not diffs:
        return None
    nz = [x for x in diffs if abs(x) > 1e-12]
    return {"requests": len(diffs), "F000": round(sum(f0) / len(f0), 4),
            "F010": round(sum(f0) / len(f0) + sum(diffs) / len(diffs), 4),
            "higher": sum(x > 1e-12 for x in diffs), "lower": sum(x < -1e-12 for x in diffs),
            "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0}


def main(args):
    turns = first_turns()
    out = []
    for arg in args:
        folder, _, mode = arg.partition(":")
        rows = list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")))
        groups = grouped_available(rows, turns) if mode == "available" else units(rows, turns)
        unparsed = sum(r["parsed_ok"] != "1" for rs in groups.values() for r in rs)
        for metric in METRICS:
            for parsed_only in (False, True):
                res = contrast(groups, metric, parsed_only)
                if res:
                    out.append({"model": folder.split("__")[0].replace("local_", ""), "metric": metric,
                                "answers": "parseable only" if parsed_only else "all (primary)",
                                "unparseable_in_units": unparsed, **res})
    with (HERE / "e1-parse-sensitivity.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(f"{r['model'][:20]:20} {r['metric'][:12]:12} {r['answers']:15} unparsed={r['unparseable_in_units']:3} "
              f"n={r['requests']} {r['F000']:.2f}->{r['F010']:.2f} +{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.2g}")


if __name__ == "__main__":
    main(sys.argv[1:])
