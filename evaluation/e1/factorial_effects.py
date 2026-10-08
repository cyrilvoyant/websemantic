"""Main effects of the 2^3 factorial (O ontology+SHACL, C LLM contract, P FAIR files) on first-turn behaviour.

Reads the scorer output e1-scores-<folder>.csv of each answer folder given on the command line. For each software,
metric and factor, the proportion with the factor is compared with the proportion without it (the other two factors
pooled). Rows (cases x repetitions) are not independent: the Fisher p-value in the CSV is kept for traceability only
and is not shown on the figure; inference is made at request level (paired, de-duplicated analysis). Output: e1-factorial-effects.csv and figure e1-factorial-effects.{pdf,png} (private).
"""

import csv
import sys
from pathlib import Path

from scipy.stats import fisher_exact

HERE = Path(__file__).resolve().parent
FACTORS = {"O": 1, "C": 2, "P": 3}          # position of the factor letter in "F<O><C><P>"
METRICS = {"decision_ok": "correct decision", "premature_execute": "premature execution",
           "hallucination": "hallucination", "qualifier_convention_ok": "qualifier handled"}
DOMAINS = {"tls": "TLS", "lqlequiv": "LQL-Equiv", "pyrcel": "pyrcel"}


def flag(v):
    return None if v in ("", None) else float(v) > 0


def effects(folder):
    rows = list(csv.DictReader((HERE / f"e1-scores-{folder}.csv").open(encoding="utf-8")))
    out = []
    for dom in DOMAINS:
        for m in METRICS:
            for fac, pos in FACTORS.items():
                cnt = {True: [0, 0], False: [0, 0]}          # with factor? -> [successes, n]
                for r in rows:
                    if r["domain"] != dom or not r["condition"].startswith("F"):
                        continue
                    v = flag(r.get(m))
                    if v is None:
                        continue
                    w = r["condition"][pos] == "1"
                    cnt[w][0] += v
                    cnt[w][1] += 1
                (a, n1), (b, n0) = cnt[True], cnt[False]
                if not n1 or not n0:
                    continue
                p = fisher_exact([[a, n1 - a], [b, n0 - b]])[1]
                out.append({"model": folder.split("__")[0], "domain": dom, "metric": m, "factor": fac,
                            "with": round(a / n1, 4), "n_with": n1, "without": round(b / n0, 4), "n_without": n0,
                            "difference": round(a / n1 - b / n0, 4), "fisher_p": p})
    return out


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False})
    models = sorted({r["model"] for r in rows})
    shown = ["decision_ok", "premature_execute", "qualifier_convention_ok"]
    fig, ax = plt.subplots(len(shown), len(DOMAINS), figsize=(10, 2.3 * len(shown)), sharey="row")
    colors = ["#3b6182", "#b5523b", "#6b8f71", "#8a6aa8"]
    width = 0.8 / len(models)
    for i, m in enumerate(shown):
        for j, dom in enumerate(DOMAINS):
            a = ax[i][j]
            for k, model in enumerate(models):
                sel = {r["factor"]: r for r in rows if r["model"] == model and r["domain"] == dom and r["metric"] == m}
                xs = [x + (k - (len(models) - 1) / 2) * width for x in range(len(FACTORS))]
                for x, f in zip(xs, FACTORS):  # a missing metric is shown as ND, never as a zero difference
                    if f in sel:
                        a.bar(x, sel[f]["difference"], width, color=colors[k % len(colors)],
                              label=model if (i, j, f) == (0, 0, "O") else None)
                    else:
                        a.text(x, 0, "ND", ha="center", va="bottom", fontsize=7, color="grey")
            a.axhline(0, color="black", lw=0.6)
            a.set_xticks(range(len(FACTORS)), ["ontology (O)", "contract (C)", "FAIR files (P)"])
            if i == 0:
                a.set_title(DOMAINS[dom])
            if j == 0:
                a.set_ylabel(f"Δ {METRICS[m]}\n(with − without)")
    fig.legend(loc="upper center", ncol=len(models), frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"e1-factorial-effects.{ext}", dpi=200, bbox_inches="tight")


def main(folders):
    rows = [r for f in folders for r in effects(f)]
    with (HERE / "e1-factorial-effects.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    plot(rows)
    for r in rows:
        if r["metric"] in ("decision_ok", "premature_execute"):
            print(f"{r['model'][:22]:22} {r['domain']:9} {r['metric']:18} {r['factor']}  "
                  f"{r['without']:.2f} -> {r['with']:.2f}  p={r['fisher_p']:.3g}")


if __name__ == "__main__":
    main(sys.argv[1:])
