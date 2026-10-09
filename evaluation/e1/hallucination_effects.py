"""Hallucinations in first-turn answers (request of Cyril, 9 October 2026), same design as request_level.py.

Per answer, from score_e1.py: unsupported = number of values without evidence in the request (invented values);
silent_qualifier_acceptance = a qualifier convention applied without asking; silent_default = a default applied without
acceptance; hallucination = at least one of the three. Each is turned into a 0/1 indicator per answer, averaged per
request and condition, and the main effect of O, C and P is tested with the Wilcoxon signed-rank test (zero
differences discarded), per code and pooled; Holm over all contrasts of this table. Descriptive companion of the
primary analysis, not preregistered.
Output: e1-hallucination.csv (private).
Usage: python hallucination_effects.py <folder> [...]
"""

import csv
import sys
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from length_control import holm  # noqa: E402
from request_level import DOMAINS, FACTORS, first_turns, units  # noqa: E402

INDICATORS = {"hallucination": "hallucination", "unsupported": "unsupported",
              "silent_qualifier_acceptance": "silent qualifier", "silent_default": "silent default"}


def flag(r, key):
    v = r.get(key)
    return None if v in ("", None) else float(float(v) > 0)


def main(folders):
    turns = first_turns()
    rows = []
    for folder in folders:
        data = list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")))
        grouped = units(data, turns)
        model = folder.split("__")[0].replace("local_", "")
        for d in [*DOMAINS, "all"]:
            for key in INDICATORS:
                for f, pos in FACTORS.items():
                    diffs, w_m, wo_m = [], [], []
                    for (dom, _), rs in grouped.items():
                        if d != "all" and dom != d:
                            continue
                        w = [flag(r, key) for r in rs if r["condition"][pos] == "1" and flag(r, key) is not None]
                        wo = [flag(r, key) for r in rs if r["condition"][pos] == "0" and flag(r, key) is not None]
                        if w and wo:
                            a, b = sum(w) / len(w), sum(wo) / len(wo)
                            w_m.append(a); wo_m.append(b); diffs.append(a - b)
                    if not diffs:
                        continue
                    nz = [x for x in diffs if abs(x) > 1e-12]
                    rows.append({"model": model, "domain": d, "indicator": key, "factor": f, "requests": len(diffs),
                                 "without": round(sum(wo_m) / len(wo_m), 4), "with": round(sum(w_m) / len(w_m), 4),
                                 "difference": round(sum(diffs) / len(diffs), 4),
                                 "higher": sum(x > 1e-12 for x in diffs), "lower": sum(x < -1e-12 for x in diffs),
                                 "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0})
    for r, p in zip(rows, holm([r["wilcoxon_p"] for r in rows])):
        r["holm_p"] = p  # full precision
    with (HERE / "e1-hallucination.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if r["domain"] == "all":
            print(f"{r['model'][:14]:14} {INDICATORS[r['indicator']][:16]:16} {r['factor']} n={r['requests']} "
                  f"{r['without']:.2f}->{r['with']:.2f} +{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.2g} holm={r['holm_p']:.2g}")


if __name__ == "__main__":
    main(sys.argv[1:])
