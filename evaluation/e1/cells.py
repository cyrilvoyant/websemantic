"""Cell means of the 2^3 design and the simple contrast documentation alone -> documentation + contract (F000 -> F010).

Codex synthesis of the external reviews (9 October 2026): the marginal effect of C (Eq. 1) averages over O and P; the
practical question "what does adding the contract to the documentation change?" is the simple contrast F010 - F000.
Same unit as request_level.py (unique first-turn request, complete blocks, repetitions averaged), Wilcoxon signed-rank
(zero differences discarded), Holm over the 36 simple contrasts (3 models x 3 metrics x 4 groupings). Descriptive
complement of the preregistered analysis.
Outputs (private): e1-cells.csv (mean per model, code, condition, metric) and e1-simple-contract.csv.
Usage: python cells.py <folder> [...]
"""

import csv
import sys
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from length_control import holm  # noqa: E402
from request_level import DOMAINS, METRICS, first_turns, units  # noqa: E402

CONDS = [f"F{i:03b}" for i in range(8)]


def unit_means(rs, metric):
    out = {}
    for c in CONDS:
        v = [float(r[metric]) for r in rs if r["condition"] == c and r[metric] not in ("", None)]
        if v:
            out[c] = sum(v) / len(v)
    return out


def main(folders):
    turns = first_turns()
    cells, simple = [], []
    for folder in folders:
        model = folder.split("__")[0].replace("local_", "")
        grouped = units(list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8"))), turns)
        for d in [*DOMAINS, "all"]:
            sel = {k: rs for k, rs in grouped.items() if d == "all" or k[0] == d}
            for m in METRICS:
                means = [unit_means(rs, m) for rs in sel.values()]
                for c in CONDS:
                    v = [u[c] for u in means if c in u]
                    if v:
                        cells.append({"model": model, "domain": d, "metric": m, "condition": c, "requests": len(v),
                                      "mean": round(sum(v) / len(v), 4)})
                diffs = [u["F010"] - u["F000"] for u in means if "F010" in u and "F000" in u]
                if diffs:
                    nz = [x for x in diffs if abs(x) > 1e-12]
                    f0 = [u["F000"] for u in means if "F010" in u and "F000" in u]
                    simple.append({"model": model, "domain": d, "metric": m, "requests": len(diffs),
                                   "F000": round(sum(f0) / len(f0), 4),
                                   "F010": round(sum(f0) / len(f0) + sum(diffs) / len(diffs), 4),
                                   "difference": round(sum(diffs) / len(diffs), 4),
                                   "higher": sum(x > 1e-12 for x in diffs), "lower": sum(x < -1e-12 for x in diffs),
                                   "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0})
    for r, p in zip(simple, holm([r["wilcoxon_p"] for r in simple])):
        r["holm_p"] = p
    for name, rows in (("e1-cells.csv", cells), ("e1-simple-contract.csv", simple)):
        with (HERE / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    for r in simple:
        if r["domain"] == "all":
            print(f"{r['model'][:14]:14} {r['metric'][:12]:12} n={r['requests']} {r['F000']:.2f}->{r['F010']:.2f} "
                  f"+{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.2g} holm={r['holm_p']:.2g}")


if __name__ == "__main__":
    main(sys.argv[1:])
