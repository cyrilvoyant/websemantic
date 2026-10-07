"""Numerical consequence of each E1 interpretation (execute answers on cases with a reference).

Replay happens only when the candidate itself supplied every expected field
(no completion from the private reference). The candidate configuration is run on
the pinned backend and compared with the reference run on an identical support
(same length and same time stamps; otherwise "support_differs", no truncation):
RMSE and nRMSE = RMSE / mean(reference); RMSE only when |mean| is negligible
(signed quantities such as supersaturation). Relative KPI error is undefined for a
zero reference. Usage: python numeric_e1.py <model> <domain>   (pyrcel needs its env).
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


def rmse(a, b):
    """RMSE and nRMSE (normalised by the reference mean); refuses different supports."""
    if len(a) != len(b):
        return None, None
    n = len(b)
    e = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)) / n)
    mean = sum(b) / n
    rms = math.sqrt(sum(x * x for x in b) / n)
    negligible = abs(mean) <= 0.05 * rms if rms > 0 else True
    return e, (None if negligible else e / abs(mean))


def rel_err(x, ref):
    return None if ref == 0 else abs(x - ref) / abs(ref)


def complete(case, answer):
    """True if the candidate gave a value for every expected field (no completion from the reference)."""
    got = llm_values(answer)
    return all(k in got for k in expected(case))


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
    got = dict(ref)  # fields outside expected(): declared defaults accepted by the case itself
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = type(ref[k])(v) if isinstance(ref[k], (int, float)) and not isinstance(v, str) else v
    grid_same = all(str(got[k]) == str(ref[k]) for k in ("start_date", "n_days", "freq_minutes"))
    p_ref, e_ref = tls_run(ref)
    try:
        p_got, e_got = tls_run(got)
    except Exception as exc:  # noqa: BLE001 - any backend failure is recorded as an outcome  # invalid configuration reached the backend
        return {"status": f"backend_error: {type(exc).__name__}"}
    r = {"status": "ok" if grid_same else "support_differs", "grid_same": int(grid_same), "quantity": "power_kw",
         "kpi": "total_mwh", "kpi_rel_err": rel_err(e_got, e_ref)}
    if grid_same:
        r["rmse"], r["nrmse"] = rmse(p_got, p_ref)
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
    return {"status": "ok", "grid_same": 1, "quantity": "eqd_oar_total",
            "abs_err_eqd_oar": abs(o - o_ref), "abs_err_eqd_tumour": abs(t - t_ref),
            "kpi": "eqd_oar_total", "kpi_rel_err": rel_err(o, o_ref), "kpi2_rel_err": rel_err(t, t_ref)}


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
        return list(o.S), list(o.time), o.summary["S_max"]
    s_ref, t_ref, smax_ref = run(exp)
    try:
        s, t, smax = run(got)
    except Exception as exc:  # noqa: BLE001 - any backend failure is recorded as an outcome
        return {"status": f"backend_error: {type(exc).__name__}"}
    same_support = len(t) == len(t_ref) and all(abs(a - b) < 1e-9 for a, b in zip(t, t_ref))
    r = {"status": "ok" if same_support else "support_differs", "grid_same": int(same_support), "quantity": "S",
         "kpi": "S_max", "kpi_rel_err": rel_err(smax, smax_ref)}
    if same_support:
        r["rmse"], r["nrmse"] = rmse(s, s_ref)
    return r


def main():
    model, domain = sys.argv[1], sys.argv[2]
    fn = {"tls": tls_case, "lqlequiv": lql_case, "pyrcel": pyrcel_case}[domain]
    cases = {json.loads(line)["id"]: json.loads(line) for line in (RESERVE / domain / "pilot.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    rows = []
    for f in sorted((RESERVE / "runs" / "e1" / model).glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("domain") != domain or (a.get("parsed") or {}).get("decision") != "execute":
            continue
        c = cases.get(a["case_id"])
        if c is None:  # qualifier cases have no numerical reference (decision and convention only)
            continue
        if not expected(c) or (domain == "tls" and not c.get("reference_scenarios")):
            continue
        if c.get("variants") or c.get("modifications") or c.get("expected_turn_decisions"):
            continue  # E1 scores the first turn only; these references include later turns
        if not complete(c, a):
            r = {"case_id": c["id"], "condition": a["condition"], "rep": a["rep"], "status": "incomplete_candidate"}
        else:
            r = {"case_id": c["id"], "condition": a["condition"], "rep": a["rep"], **fn(c, a)}
        r["instructions"] = a.get("instructions_sha256_12", "v0")
        rows.append(r)
        print(r, flush=True)
    keys = sorted({k for r in rows for k in r})
    with open(REPO / "evaluation" / "e1" / f"e1-numeric-{model}-{domain}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
