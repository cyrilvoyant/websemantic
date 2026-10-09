"""Generic clarification policy (evaluation/PREREG-generic-policy.md): G vs F000 and F010 vs G.

Unit: unique first-turn request, repetitions averaged (same as request_level.py). Paired Wilcoxon signed-rank, zero
differences discarded; Holm over the four primary tests on premature execution (two contrasts x two open models).
Usage: python generic_effect.py <campaign_folder>:<generic_folder> [...]   (one pair per model)
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from length_control import holm  # noqa: E402
from request_level import first_turns  # noqa: E402

METRICS = ("premature_execute", "decision_ok", "qualifier_convention_ok", "unsupported")
CONTRASTS = (("G", "F000"), ("F010", "G"), ("F010", "F000"))


def means(folders, turns):
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for folder in folders:
        for r in csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")):
            if r["condition"] not in ("F000", "F010", "G"):
                continue
            for m in METRICS:
                v = r.get(m)
                if v not in ("", None):
                    acc[(r["domain"], turns[r["case_id"]])][r["condition"]][m].append(float(float(v) > 0) if m == "unsupported" else float(v))
    return {u: {c: {m: sum(v) / len(v) for m, v in ms.items()} for c, ms in cs.items()} for u, cs in acc.items()}


def main(pairs):
    turns = first_turns()
    rows = []
    for pair in pairs:
        campaign, generic = pair.split(":")
        data = means([campaign, generic], turns)
        model = generic.split("__")[0].replace("local_", "")
        for a, b in CONTRASTS:
            for m in METRICS:
                for dom in ("all", "tls", "lqlequiv", "pyrcel"):
                    d = [cs[a][m] - cs[b][m] for (u, _), cs in data.items()
                         if (dom == "all" or u == dom) and m in cs.get(a, {}) and m in cs.get(b, {})]
                    if not d:
                        continue
                    nz = [x for x in d if abs(x) > 1e-12]
                    rows.append({"model": model, "contrast": f"{a} vs {b}", "metric": m, "domain": dom, "requests": len(d),
                                 "mean_difference": round(sum(d) / len(d), 4), "higher": sum(x > 1e-12 for x in d),
                                 "lower": sum(x < -1e-12 for x in d),
                                 "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0})
    primary = [r for r in rows if r["metric"] == "premature_execute" and r["domain"] == "all"
               and r["contrast"] in ("G vs F000", "F010 vs G") and r["model"] in ("mistral-small-3.2-24b", "qwen2.5-72b")]
    for r, p in zip(primary, holm([r["wilcoxon_p"] for r in primary])):
        r["holm_p"] = p
    with (HERE / "e1-generic.csv").open("w", newline="", encoding="utf-8") as fh:
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
