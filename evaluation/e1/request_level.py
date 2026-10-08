"""Request-level main effects of the 2^3 factorial with Wilcoxon signed-rank tests.

Unit of analysis: the unique first-turn request (identical first turns merged), restricted to complete blocks
(8 conditions x 3 repetitions, one instruction version). For each unit, factor and metric: mean over the four
conditions with the factor minus mean over the four without (repetitions averaged). The paired differences are tested
with the Wilcoxon signed-rank test (zero differences discarded, Wilcoxon's method). Same unit definition as Codex's
work/review-20261008/paired_factorial.py, so the proportions can be cross-checked.
Output: e1-request-level.csv and figure e1-request-level.{pdf,png} (private).
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
RESERVE = HERE.parents[2] / "benchmark-reserve"
FACTORS = {"O": 1, "C": 2, "P": 3}
METRICS = {"decision_ok": "correct decision", "premature_execute": "premature execution",
           "qualifier_convention_ok": "qualifier handled"}
DOMAINS = {"tls": "TLS", "lqlequiv": "LQL-Equiv", "pyrcel": "pyrcel"}
CONDS = {f"F{i:03b}" for i in range(8)}


def first_turns():
    out = {}
    for d in DOMAINS:
        for corpus in ("pilot", "qualifiers"):
            for line in (RESERVE / d / f"{corpus}.jsonl").read_text(encoding="utf-8").splitlines():
                if line.strip():
                    c = json.loads(line)
                    out[c["id"]] = c["turns"][0].strip()
    return out


def units(rows, turns):
    by_case = defaultdict(list)
    for r in rows:
        by_case[(r["domain"], r["case_id"])].append(r)
    grouped = defaultdict(list)
    for (d, cid), rs in by_case.items():
        if len(rs) == 24 and {r["condition"] for r in rs} == CONDS and len({r["instructions"] for r in rs}) == 1:
            grouped[(d, turns[cid])].extend(rs)
    return grouped


def value(v):
    return None if v in ("", None) else float(v)


def analyse(folder, turns):
    rows = list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")))
    out = []
    grouped = units(rows, turns)
    for d in [*DOMAINS, "all"]:  # "all": the three software pooled, one unit per unique request
        for m in METRICS:
            for f, pos in FACTORS.items():
                diffs, w_means, wo_means = [], [], []
                for (dom, _), rs in grouped.items():
                    if d != "all" and dom != d:
                        continue
                    w = [value(r[m]) for r in rs if r["condition"][pos] == "1" and value(r[m]) is not None]
                    wo = [value(r[m]) for r in rs if r["condition"][pos] == "0" and value(r[m]) is not None]
                    if w and wo:
                        a, b = sum(w) / len(w), sum(wo) / len(wo)
                        w_means.append(a)
                        wo_means.append(b)
                        diffs.append(a - b)
                if not diffs:
                    continue
                nz = [x for x in diffs if abs(x) > 1e-12]
                p = wilcoxon(nz).pvalue if len(nz) >= 1 else 1.0
                out.append({"model": folder.split("__")[0].replace("local_", ""), "domain": d, "metric": m, "factor": f,
                            "requests": len(diffs), "without": round(sum(wo_means) / len(wo_means), 4),
                            "with": round(sum(w_means) / len(w_means), 4),
                            "difference": round(sum(diffs) / len(diffs), 4),
                            "improved": sum(x > 1e-12 for x in diffs), "worsened": sum(x < -1e-12 for x in diffs),
                            "wilcoxon_p": round(float(p), 6)})
    return out


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False})
    models = sorted({r["model"] for r in rows})
    fig, ax = plt.subplots(len(METRICS), len(DOMAINS), figsize=(10, 2.3 * len(METRICS)), sharey="row")
    colors = ["#3b6182", "#b5523b", "#6b8f71", "#8a6aa8"]
    width = 0.8 / len(models)
    for i, m in enumerate(METRICS):
        for j, d in enumerate(DOMAINS):
            a = ax[i][j]
            for k, model in enumerate(models):
                sel = {r["factor"]: r for r in rows if r["model"] == model and r["domain"] == d and r["metric"] == m}
                for x, f in enumerate(FACTORS):
                    xx = x + (k - (len(models) - 1) / 2) * width
                    if f in sel:
                        a.bar(xx, sel[f]["difference"], width, color=colors[k % len(colors)],
                              label=model if (i, j, f) == (0, 0, "O") else None)
                    else:
                        a.text(xx, 0, "ND", ha="center", va="bottom", fontsize=7, color="grey")
            a.axhline(0, color="black", lw=0.6)
            a.set_xticks(range(len(FACTORS)), ["ontology (O)", "contract (C)", "FAIR files (P)"])
            if i == 0:
                a.set_title(DOMAINS[d])
            if j == 0:
                a.set_ylabel(f"Δ {METRICS[m]}\n(with − without)")
    fig.legend(loc="upper center", ncol=len(models), frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"e1-request-level.{ext}", dpi=200, bbox_inches="tight")


def main(folders):
    turns = first_turns()
    rows = [r for f in folders for r in analyse(f, turns)]
    with (HERE / "e1-request-level.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    plot(rows)
    for r in rows:
        print(f"{r['model'][:16]:16} {r['domain']:9} {r['metric'][:12]:12} {r['factor']} n={r['requests']:2} "
              f"{r['without']:.2f}->{r['with']:.2f} +{r['improved']}/-{r['worsened']} p={r['wilcoxon_p']:.3g}")


if __name__ == "__main__":
    main(sys.argv[1:])
