"""Interim analysis of a campaign still running (Gemini, free tier): repetitions available so far.

Units: unique first-turn requests with an answer in all eight conditions for the selected repetitions (answers
averaged), same contrasts as request_level.py (marginal effect of C) and cells.py (cell means, F000 -> F010), Wilcoxon
signed-rank, zero differences discarded. Interim and descriptive: the analysis of record is rerun on the complete
campaign. Usage: python partial_rep.py <folder> <reps, e.g. 1 or 1,2>
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from request_level import METRICS, first_turns  # noqa: E402

CONDS = [f"F{i:03b}" for i in range(8)]


def main(folder, reps):
    turns = first_turns()
    rows = [r for r in csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")) if r["rep"] in reps]
    by = defaultdict(list)
    for r in rows:
        by[(r["domain"], turns[r["case_id"]])].append(r)
    units = {k: v for k, v in by.items() if {r["condition"] for r in v} == set(CONDS)}
    print(f"{folder} reps {','.join(reps)}: {len(rows)} answers, {len(units)} complete requests of {len(by)}")

    def mean(rs, m, keep):
        v = [float(r[m]) for r in rs if r[m] not in ("", None) and keep(r["condition"])]
        return sum(v) / len(v) if v else None

    for m in METRICS:
        for name, a_keep, b_keep in (("marginal C", lambda c: c[2] == "1", lambda c: c[2] == "0"),
                                     ("F000->F010", lambda c: c == "F010", lambda c: c == "F000")):
            pairs = [(mean(rs, m, a_keep), mean(rs, m, b_keep)) for rs in units.values()]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
            d = [a - b for a, b in pairs]
            nz = [x for x in d if abs(x) > 1e-12]
            print(f"  {m[:12]:12} {name:10} n={len(d):2} {sum(b for _, b in pairs) / len(pairs):.2f}->"
                  f"{sum(a for a, _ in pairs) / len(pairs):.2f} +{sum(x > 0 for x in d)}/-{sum(x < 0 for x in d)} "
                  f"p={wilcoxon(nz).pvalue if nz else 1.0:.2g}")
        cells = [mean(rs, m, lambda c, k=k: c == k) for k in CONDS for rs in [None]] if False else None
        vals = []
        for k in CONDS:
            v = [mean(rs, m, lambda c, k=k: c == k) for rs in units.values()]
            v = [x for x in v if x is not None]
            vals.append(f"{k}:{sum(v) / len(v):.2f}")
        print("   cells", " ".join(vals))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","))
