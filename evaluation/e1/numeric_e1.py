"""Numerical consequence of each E1 interpretation (execute answers on cases with a reference).

The reference configuration is overridden by the values the LLM returned for the
same fields, then run deterministically on the pinned backend and compared with
the reference run: RMSD and nRMSD = RMSD / RMS(reference) on the same grid,
relative error on scalar indicators. A changed time grid is reported, not
interpolated. Usage: python numeric_e1.py <model> <domain>   (pyrcel needs its env).
"""

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESERVE = REPO.parent / "benchmark-reserve"
sys.path.insert(0, str(Path(__file__).parent))
from score_e1 import expected, norm


def rmsd(a, b):
    n = min(len(a), len(b))
    d = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)) / n)
    rms = math.sqrt(sum(b[i] ** 2 for i in range(n)) / n)
    return d, (d / rms if rms > 0 else None)


def llm_values(answer):
    out = {}
    for v in (answer.get("parsed") or {}).get("values") or []:
        if isinstance(v, dict) and v.get("value") is not None:
            out[norm(v.get("field", ""))] = v["value"]
    return out


# ---------- TLS ----------
def tls_run(values):
    sys.path.insert(0, str(REPO / "external/tunnel-load-simulator/src"))
    import pandas as pd
    from tunnel_load_simulator.simulator import TunnelConfig, run_monte_carlo
    fields = TunnelConfig.__dataclass_fields__
    cfg = TunnelConfig(**{k: values[k] for k in fields})
    out = run_monte_carlo(cfg, pd.Timestamp(values["start_date"]), int(values["n_days"]), int(values["freq_minutes"]),
                          int(values["n_runs"]), int(values["base_seed"]))
    return list(out["representative"]["power_kw"]), float(out["kpis"]["total_mwh"].median())


def tls_case(case, answer):
    ref_doc = json.loads((RESERVE / "tls" / case["reference_scenarios"][0]).read_text(encoding="utf-8"))["scenario"]
    ref = {k: v["value"] for g in ("inputs", "experiment") for k, v in ref_doc[g].items()}
    got = dict(ref)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = type(ref[k])(v) if isinstance(ref[k], (int, float)) and not isinstance(v, str) else v
    grid_same = all(str(got[k]) == str(ref[k]) for k in ("start_date", "n_days", "freq_minutes"))
    p_ref, e_ref = tls_run(ref)
    try:
        p_got, e_got = tls_run(got)
    except Exception as exc:  # noqa: BLE001 - any backend failure is recorded as an outcome  # invalid configuration reached the backend
        return {"status": f"backend_error: {type(exc).__name__}"}
    r = {"status": "ok", "grid_same": int(grid_same), "quantity": "power_kw",
         "kpi": "total_mwh", "kpi_rel_err": abs(e_got - e_ref) / abs(e_ref)}
    if grid_same:
        r["rmsd"], r["nrmsd"] = rmsd(p_got, p_ref)
    return r


# ---------- LQL ----------
def lql_case(case, answer):
    sys.path.insert(0, str(REPO / "external/LQL-Equiv-web/src"))
    from lqlequiv import Course, Prescription, compute, load_library
    lib = load_library()
    exp = expected(case)
    got = dict(exp)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = v

    def run(x):
        plan = Prescription(courses=(Course(float(x["dose_per_fraction"]), float(x["n_fractions"])),),
                            reference_dose=float(x["reference_dose"]))
        res = compute(lib.organ(x["organ"]), lib.tumour_site(x["tumour_site"]), plan)
        return res.eqd_oar_total, res.eqd_tumour_total
    o_ref, t_ref = run(exp)
    try:
        o, t = run(got)
    except Exception as exc:  # noqa: BLE001 - any backend failure is recorded as an outcome
        return {"status": f"backend_error: {type(exc).__name__}"}
    return {"status": "ok", "grid_same": 1, "quantity": "eqd_oar_total,eqd_tumour_total",
            "rmsd": math.sqrt(((o - o_ref) ** 2 + (t - t_ref) ** 2) / 2),
            "kpi": "eqd_oar_total", "kpi_rel_err": abs(o - o_ref) / abs(o_ref)}


# ---------- pyrcel ----------
def pyrcel_case(case, answer):
    import pyrcel as pm
    ref = case["reference"]
    exp = expected(case)
    got = dict(exp)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = float(v)

    def run(x):
        aer = [pm.AerosolSpecies("a", pm.Lognorm(mu=x["mu"], sigma=x["sigma"], N=x["n"]), kappa=x["kappa"], bins=ref["bins"])]
        m = pm.ParcelModel(aer, V=x["v"], T0=x["t0"], S0=x["s0"], P0=x["p0"], accom=ref["accom"], console=False)
        o = m.run(t_end=ref["t_end"], output_dt=ref["output_dt"], terminate=ref["terminate"], terminate_depth=ref["terminate_depth"])
        return list(o.S), o.summary["S_max"]
    s_ref, smax_ref = run(exp)
    try:
        s, smax = run(got)
    except Exception as exc:  # noqa: BLE001 - any backend failure is recorded as an outcome
        return {"status": f"backend_error: {type(exc).__name__}"}
    d, nd = rmsd(s, s_ref)
    return {"status": "ok", "grid_same": int(len(s) == len(s_ref)), "quantity": "S", "rmsd": d, "nrmsd": nd,
            "kpi": "S_max", "kpi_rel_err": abs(smax - smax_ref) / abs(smax_ref)}


def main():
    model, domain = sys.argv[1], sys.argv[2]
    fn = {"tls": tls_case, "lqlequiv": lql_case, "pyrcel": pyrcel_case}[domain]
    cases = {json.loads(line)["id"]: json.loads(line) for line in (RESERVE / domain / "pilot.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    rows = []
    for f in sorted((RESERVE / "runs" / "e1" / model).glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("domain") != domain or (a.get("parsed") or {}).get("decision") != "execute":
            continue
        c = cases[a["case_id"]]
        if not expected(c) or (domain == "tls" and not c.get("reference_scenarios")):
            continue
        if c.get("variants") or c.get("modifications") or c.get("expected_turn_decisions"):
            continue  # E1 scores the first turn only; these references include later turns
        r = {"case_id": c["id"], "condition": a["condition"], "rep": a["rep"], **fn(c, a)}
        rows.append(r)
        print(r, flush=True)
    keys = sorted({k for r in rows for k in r})
    with open(REPO / "evaluation" / "e1" / f"e1-numeric-{model}-{domain}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
