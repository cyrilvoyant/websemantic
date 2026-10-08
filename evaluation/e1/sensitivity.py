"""Sensitivity of the pooled contract effect (Codex review, 8 October 2026).

Same unit and test as request_level.py (unique first-turn request, four conditions with C against four without,
Wilcoxon signed-rank). Three checks, per model:
  - leave one code out, and leave one corpus family out (units containing that family are removed), to show that the
    pooled effect does not rest on one code or one family of related scenarios;
  - joint endpoint for answers without a recognised decision: counted as premature execution (worst case) instead of
    not premature, so that an unusable answer can never pass as valid handling.
Output: e1-sensitivity.csv (private) and a printed summary.
Usage: python sensitivity.py <campaign_folder> [...]
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from request_level import first_turns, units  # noqa: E402

METRICS = ("premature_execute", "qualifier_convention_ok", "decision_ok")


def effect(grouped, metric, keep, worst_case=False):
    diffs = []
    for key, rs in grouped.items():
        if not keep(key, rs):
            continue
        vals = defaultdict(list)
        for r in rs:
            v = r[metric]
            if worst_case and metric == "premature_execute" and r["parsed_ok"] != "1":
                v = "1"
            if v not in ("", None):
                vals[r["condition"][2] == "1"].append(float(v))
        if vals[True] and vals[False]:
            diffs.append(sum(vals[True]) / len(vals[True]) - sum(vals[False]) / len(vals[False]))
    nz = [d for d in diffs if abs(d) > 1e-12]
    p = float(wilcoxon(nz).pvalue) if nz else 1.0
    return len(diffs), sum(diffs) / len(diffs) if diffs else 0.0, sum(d > 1e-12 for d in diffs), sum(d < -1e-12 for d in diffs), p


def main(folders):
    turns = first_turns()
    rows = []
    for folder in folders:
        model = folder.split("__")[0].replace("local_", "")
        data = list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")))
        grouped = units(data, turns)
        fams = sorted({r["family"] for r in data})
        checks = [("all", lambda k, rs: True, False)]
        checks += [(f"without code {d}", (lambda d: lambda k, rs: k[0] != d)(d), False) for d in ("tls", "lqlequiv", "pyrcel")]
        checks += [(f"without family {f}", (lambda f: lambda k, rs: all(r["family"] != f for r in rs))(f), False) for f in fams]
        checks += [("unusable = premature", lambda k, rs: True, True)]
        for metric in METRICS:
            for name, keep, worst in checks:
                if worst and metric != "premature_execute":
                    continue
                n, mean, up, down, p = effect(grouped, metric, keep, worst)
                rows.append({"model": model, "metric": metric, "check": name, "requests": n,
                             "difference": round(mean, 4), "higher": up, "lower": down, "wilcoxon_p": round(p, 6)})
    with (HERE / "e1-sensitivity.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for model in dict.fromkeys(r["model"] for r in rows):
        for metric in METRICS:
            sub = [r for r in rows if r["model"] == model and r["metric"] == metric and r["check"] != "all"]
            base = next(r for r in rows if r["model"] == model and r["metric"] == metric and r["check"] == "all")
            lo = min(sub, key=lambda r: abs(r["difference"]))
            hi_p = max(sub, key=lambda r: r["wilcoxon_p"])
            print(f"{model[:14]:14} {metric[:12]:12} all {base['difference']:+.3f} p={base['wilcoxon_p']:.2g} | "
                  f"smallest |effect| {lo['difference']:+.3f} ({lo['check']}) | largest p {hi_p['wilcoxon_p']:.2g} ({hi_p['check']})")
    for r in rows:
        if r["check"] == "unusable = premature":
            print(r)


if __name__ == "__main__":
    main(sys.argv[1:])
