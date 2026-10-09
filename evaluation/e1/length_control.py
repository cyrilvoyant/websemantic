"""Preregistered contextual control (evaluation/PREREG-length-control.md): L2/L3 against F010/F110.

Unit: unique first-turn request (identical first turns merged), repetitions averaged, same definition as
request_level.py. For each model, contrasts L3 vs F010, L3 vs F110 and L2 vs F010 are tested with the paired Wilcoxon
signed-rank test (zero differences discarded), three software pooled; Holm correction over the six primary
premature-execution tests (three contrasts x two models). Other metrics and per-software values are descriptive.
Usage: python length_control.py <campaign_folder>:<control_folder> [...]   (one pair per model)
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from request_level import first_turns

METRICS = ("premature_execute", "decision_ok", "qualifier_convention_ok")
CONTRASTS = (("L3", "F010"), ("L3", "F110"), ("L2", "F010"))


def means(folders, turns):
    """unit -> condition -> metric -> mean over the answers (repetitions, merged duplicates)."""
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for folder in folders:
        for r in csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")):
            if r["condition"] not in ("F010", "F110", "L2", "L3"):
                continue
            unit = (r["domain"], turns[r["case_id"]])
            for m in METRICS:
                if r.get(m) not in ("", None):
                    acc[unit][r["condition"]][m].append(float(r[m]))
    return {u: {c: {m: sum(v) / len(v) for m, v in ms.items()} for c, ms in cs.items()} for u, cs in acc.items()}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, running = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        running = max(running, (len(ps) - k) * ps[i])
        adj[i] = min(1.0, running)
    return adj


def main(pairs):
    turns = first_turns()
    rows = []
    for pair in pairs:
        campaign, control = pair.split(":")
        data = means([campaign, control], turns)
        model = control.split("__")[0].replace("local_", "")
        for a, b in CONTRASTS:
            for m in METRICS:
                for dom in ("all", "tls", "lqlequiv", "pyrcel"):
                    d = [cs[a][m] - cs[b][m] for (u_dom, _), cs in data.items()
                         if (dom == "all" or u_dom == dom) and m in cs.get(a, {}) and m in cs.get(b, {})]
                    if not d:
                        continue
                    nz = [x for x in d if abs(x) > 1e-12]
                    rows.append({"model": model, "contrast": f"{a} vs {b}", "metric": m, "domain": dom, "requests": len(d),
                                 "mean_difference": round(sum(d) / len(d), 4),
                                 "higher": sum(x > 1e-12 for x in d), "lower": sum(x < -1e-12 for x in d),
                                 "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0})
    primary = [r for r in rows if r["metric"] == "premature_execute" and r["domain"] == "all"]
    for r, p in zip(primary, holm([r["wilcoxon_p"] for r in primary])):
        r["holm_p"] = p  # full precision
    out = HERE / "e1-length-control.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "contrast", "metric", "domain", "requests", "mean_difference",
                                           "higher", "lower", "wilcoxon_p", "holm_p"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if r["domain"] == "all":
            print(f"{r['model'][:14]:14} {r['contrast']:11} {r['metric'][:12]:12} n={r['requests']:2} "
                  f"diff={r['mean_difference']:+.3f} +{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.3g}"
                  + (f" holm={r['holm_p']:.3g}" if "holm_p" in r else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
