"""Cell means and the simple contrast F000 -> F010 for a model completed after the main analysis (Gemini, campaign
finished on 11 October 2026), without changing the Holm family of cells.py (3 models, 36 contrasts).

Same units and tests as cells.py (unique first-turn request, complete blocks, repetitions averaged; Wilcoxon signed-rank,
zero differences discarded); Holm over this model's own contrasts (3 metrics x 4 groupings). Descriptive complement.
Outputs (private): e1-cells-<model>.csv and e1-simple-contract-<model>.csv.
Usage: python cells_extra.py <folder>
"""

import csv
import sys
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cells import CONDS, unit_means  # noqa: E402
from length_control import holm  # noqa: E402
from request_level import DOMAINS, METRICS, first_turns, units  # noqa: E402


def main(folder):
    model = folder.split("__")[0].replace("local_", "")
    grouped = units(list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8"))), first_turns())
    cells, simple = [], []
    for d in [*DOMAINS, "all"]:
        sel = {k: rs for k, rs in grouped.items() if d == "all" or k[0] == d}
        for m in METRICS:
            means = [unit_means(rs, m) for rs in sel.values()]
            for c in CONDS:
                v = [u[c] for u in means if c in u]
                if v:
                    cells.append({"model": model, "domain": d, "metric": m, "condition": c, "requests": len(v),
                                  "mean": round(sum(v) / len(v), 4)})
            pairs = [(u["F000"], u["F010"]) for u in means if "F010" in u and "F000" in u]
            if pairs:
                diffs = [b - a for a, b in pairs]
                nz = [x for x in diffs if abs(x) > 1e-12]
                f0 = sum(a for a, _ in pairs) / len(pairs)
                simple.append({"model": model, "domain": d, "metric": m, "requests": len(diffs), "F000": round(f0, 4),
                               "F010": round(f0 + sum(diffs) / len(diffs), 4),
                               "difference": round(sum(diffs) / len(diffs), 4),
                               "higher": sum(x > 1e-12 for x in diffs), "lower": sum(x < -1e-12 for x in diffs),
                               "wilcoxon_p": float(wilcoxon(nz).pvalue) if nz else 1.0})
    for r, p in zip(simple, holm([r["wilcoxon_p"] for r in simple])):
        r["holm_p"] = p
    for name, rows in ((f"e1-cells-{model}.csv", cells), (f"e1-simple-contract-{model}.csv", simple)):
        with (HERE / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    for r in cells:
        if r["domain"] == "all" and r["metric"] in ("premature_execute", "qualifier_convention_ok"):
            print(f"{r['metric'][:12]:12} {r['condition']} n={r['requests']} {r['mean']:.2f}")
    for r in simple:
        print(f"{r['domain']:8} {r['metric'][:12]:12} n={r['requests']} {r['F000']:.2f}->{r['F010']:.2f} "
              f"+{r['higher']}/-{r['lower']} p={r['wilcoxon_p']:.2g} holm={r['holm_p']:.2g}")


if __name__ == "__main__":
    main(sys.argv[1])
