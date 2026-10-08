"""What a guessed qualifier costs, in physical units (no LLM).

For each qualitative expression of the qualifier corpus, the pinned backends are run over the range of values a
reader could plausibly attach to it. The spread of every output shows the consequence of executing on a guess
instead of applying the published convention (TLS) or asking (LQL-Equiv, pyrcel).

Ranges are illustrative study choices, stated in RANGES; they are not ground truth for the expressions.
Output: evaluation/e1/e1-qualifier-sensitivity.csv (git-ignored, like the other E1 results).
"""

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import numeric_e1 as ne

# expression -> (domain, field, values tried, published convention or None when the contract says "ask")
RANGES = {
    "peu de trafic": ("tls", "traffic_level", [0.2, 0.3, 0.5, 0.7], 0.3),
    "beaucoup de trafic": ("tls", "traffic_level", [1.2, 1.5, 2.0], 1.5),
    "énormément de trafic": ("tls", "traffic_level", [1.8, 2.0, 2.5, 3.0], 2.0),
    "forte charge auxiliaire": ("tls", "aux_kw_per_km_tube", [50.0, 70.0, 90.0, 120.0], 90.0),
    "hypofractionnement modéré, 20 séances": ("lqlequiv", "dose_per_fraction", [2.5, 2.75, 3.0, 3.1], None),
    "stéréotaxie, 5 séances": ("lqlequiv", "dose_per_fraction", [6.0, 7.25, 8.0, 9.0], None),
    "forte ascendance": ("pyrcel", "V", [2.0, 3.0, 5.0, 10.0], None),
    "faible ascendance": ("pyrcel", "V", [0.1, 0.2, 0.3, 0.5], None),
}
OUTPUTS = {"tls": ["total_mwh", "peak_kw"], "lqlequiv": ["eqd_tumour_total", "ntcp_percent", "tcp_percent"],
           "pyrcel": ["S_max_percent", "Nd"]}


def tls_base():
    s = json.loads((REPO / "examples" / "tls-complete.json").read_text(encoding="utf-8"))
    v = {k: (x["value"] if isinstance(x, dict) else x) for g in ("inputs", "experiment") for k, x in s[g].items()}
    # Same tunnel as the qualifier corpus (Q-TLS-*): 2 km, 2x2 lanes, peri-urban, LED fixed, longitudinal, 7 days hourly.
    v.update(n_days=7, freq_minutes=60, n_runs=3, base_seed=42)
    return v


def run_tls(field, value):
    v = tls_base()
    v[field] = value
    k = ne.tls_run(v)["scalars"]
    return {"total_mwh": k["total_mwh"], "peak_kw": k["peak_kw"]}


def run_lql(field, value, n_fractions):
    x = {"dose_per_fraction": value, "n_fractions": n_fractions, "reference_dose": 2.0,
         "organ": "Rectum", "tumour_site": "Prostate"}
    s = ne.lql_run(x)["scalars"]
    return {k: s[k] for k in OUTPUTS["lqlequiv"]}


def run_pyrcel(field, value):
    import pyrcel as pm
    aer = [pm.AerosolSpecies("a", pm.Lognorm(mu=0.05, sigma=2.0, N=1000.0), kappa=0.54, bins=50)]
    m = pm.ParcelModel(aer, V=value, T0=283.0, S0=-0.02, P0=85000.0, accom=1.0, console=False)
    o = m.run(t_end=min(30000.0, 3000.0 / value), output_dt=1.0, terminate=True, terminate_depth=10.0)
    return {"S_max_percent": 100 * float(o.summary["S_max"]), "Nd": float(o.Nd)}


def main():
    sys.path.insert(0, str(REPO / "external" / "pyrcel"))
    rows = []
    for expr, (domain, field, values, conv) in RANGES.items():
        for value in values:
            if domain == "tls":
                out = run_tls(field, value)
            elif domain == "lqlequiv":
                out = run_lql(field, value, 20 if "20" in expr else 5)
            else:
                out = run_pyrcel(field, value)
            for name, y in out.items():
                rows.append({"expression": expr, "domain": domain, "field": field, "value": value,
                             "convention": "" if conv is None else conv, "output": name, "result": y})
            print(expr, value, {k: round(v, 3) for k, v in out.items()}, flush=True)
    path = HERE / "e1-qualifier-sensitivity.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("->", path)




def plot():
    """Three panels: TLS energy spread per expression, LQL TCP/NTCP vs dose per fraction, pyrcel droplets vs updraft."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader((HERE / "e1-qualifier-sensitivity.csv").open(encoding="utf-8")))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.4))

    tls = [e for e, r in RANGES.items() if r[0] == "tls"]
    for i, e in enumerate(tls):
        pts = [(float(r["value"]), float(r["result"])) for r in rows if r["expression"] == e and r["output"] == "total_mwh"]
        ys = [y for _, y in pts]
        ax[0].plot([min(ys), max(ys)], [i, i], color="#3b6182", lw=6, alpha=0.5, solid_capstyle="butt")
        conv = RANGES[e][3]
        yc = [y for x, y in pts if x == conv]
        if yc:
            ax[0].plot(yc, [i], "o", color="#1f2d3d", label="published convention" if i == 0 else None)
        ax[0].text(max(ys) + 2, i, f"±{50 * (max(ys) - min(ys)) / min(ys):.0f} %", fontsize=8, ha="left", va="center")
    ax[0].set_yticks(range(len(tls)), tls)
    ax[0].set_xlabel("TLS energy over 7 days (MWh)")
    ax[0].set_xlim(right=ax[0].get_xlim()[1] + 15)
    ax[0].set_title("TLS: range of plausible readings")

    for e, ls in (("hypofractionnement modéré, 20 séances", "-"), ("stéréotaxie, 5 séances", "--")):
        for out, c in (("tcp_percent", "#3b6182"), ("ntcp_percent", "#b5523b")):
            pts = sorted((float(r["value"]), float(r["result"])) for r in rows if r["expression"] == e and r["output"] == out)
            ax[1].plot(*zip(*pts), ls, marker="o", ms=3, color=c,
                       label=f"{'TCP prostate' if out == 'tcp_percent' else 'NTCP rectum'}, {e.split(',')[1].strip()}")
    ax[1].set_xlabel("dose per fraction (Gy)")
    ax[1].set_ylabel("%")
    ax[1].set_title("LQL-Equiv: dose guessed from a qualifier")

    for e, c in (("faible ascendance", "#6b8f71"), ("forte ascendance", "#3b6182")):
        pts = sorted((float(r["value"]), float(r["result"]) / 1e6) for r in rows if r["expression"] == e and r["output"] == "Nd")
        ax[2].plot(*zip(*pts), marker="o", ms=3, color=c, label=e)
    ax[2].set_xscale("log")
    ax[2].set_xlabel("updraft V (m/s)")
    ax[2].set_ylabel("activated droplets Nd (cm$^{-3}$)")
    ax[2].set_title("pyrcel: updraft guessed from a qualifier")

    handles = [h for a in ax for h in a.get_legend_handles_labels()[0]]
    labels = [lab for a in ax for lab in a.get_legend_handles_labels()[1]]
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.08), fontsize=8)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"e1-qualifier-sensitivity.{ext}", dpi=200, bbox_inches="tight")
    print("figure written")


if __name__ == "__main__":
    plot() if "--plot" in sys.argv else (main(), plot())
