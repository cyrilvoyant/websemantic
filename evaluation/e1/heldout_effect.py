"""Contract effect on held-out requests (evaluation/PREREG-heldout-extension.md): F010 vs F000.

Unit: unique first-turn request of the extension corpus, repetitions averaged. Per model: mean difference, requests
higher / lower and paired Wilcoxon signed-rank p (zero differences discarded), three codes pooled and per code; Holm
correction over the models on premature execution (primary). Families are reported descriptively.
Usage: python heldout_effect.py <folder> [...]   (one answer folder per model)
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from length_control import holm  # noqa: E402
from request_level import RESERVE  # noqa: E402

METRICS = ("premature_execute", "decision_ok")


def extension_cases():
    out = {}
    for d in ("tls", "lqlequiv", "pyrcel"):
        for line in (RESERVE / d / "extension.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                out[c["id"]] = c
    return out


def main(folders):
    cases = extension_cases()
    rows = []
    for folder in folders:
        model = folder.split("__")[0].replace("local_", "")
        acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for r in csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")):
            c = cases.get(r["case_id"])
            if c is None or r["condition"] not in ("F000", "F010"):
                continue
            unit = (c["domain"], c["family"], c["turns"][0].strip())
            for m in METRICS:
                if r.get(m) not in ("", None):
                    acc[unit][r["condition"]][m].append(float(r[m]))
        for m in METRICS:
            groups = [("all", lambda u: True)] + [(d, (lambda d: lambda u: u[0] == d)(d)) for d in ("tls", "lqlequiv", "pyrcel")]
            groups += [(f"family {f}", (lambda f: lambda u: u[1] == f)(f)) for f in sorted({u[1] for u in acc})]
            for name, keep in groups:
                d = [sum(cs["F010"][m]) / len(cs["F010"][m]) - sum(cs["F000"][m]) / len(cs["F000"][m])
                     for u, cs in acc.items() if keep(u) and cs["F010"].get(m) and cs["F000"].get(m)]
                if not d:
                    continue
                nz = [x for x in d if abs(x) > 1e-12]
                rows.append({"model": model, "metric": m, "group": name, "requests": len(d),
                             "mean_difference": round(sum(d) / len(d), 4), "higher": sum(x > 1e-12 for x in d),
                             "lower": sum(x < -1e-12 for x in d),
                             "wilcoxon_p": round(float(wilcoxon(nz).pvalue), 6) if nz else 1.0})
    primary = [r for r in rows if r["metric"] == "premature_execute" and r["group"] == "all"]
    for r, p in zip(primary, holm([r["wilcoxon_p"] for r in primary])):
        r["holm_p"] = round(p, 6)
    with (HERE / "e1-heldout.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "metric", "group", "requests", "mean_difference", "higher", "lower",
                                           "wilcoxon_p", "holm_p"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if not r["group"].startswith("family"):
            print(f"{r['model'][:14]:14} {r['metric'][:12]:12} {r['group']:9} n={r['requests']:2} diff={r['mean_difference']:+.3f} "
                  f"+{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.3g}" + (f" holm={r['holm_p']:.3g}" if "holm_p" in r else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
