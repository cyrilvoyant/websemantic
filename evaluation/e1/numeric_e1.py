"""Numerical consequence of each E1 interpretation, for every output quantity.

Replay happens only when the candidate itself supplied every expected field
(no completion from the private reference). Candidate and reference configurations
run on the pinned backend; every output is compared:
  - time series (same length and same time stamps, otherwise "support_differs",
    never truncated): RMSE and nRMSE = RMSE / mean(reference), RMSE only when the
    reference mean is negligible (|mean| <= 5 % of RMS, e.g. signed supersaturation);
  - scalar indicators: absolute error and relative error (undefined for a zero reference).
One row per (answer, quantity). Usage: python numeric_e1.py <model> <domain>
(pyrcel needs its environment).
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

TLS_SERIES = ["power_kw", "lighting_kw", "ventilation_kw", "auxiliary_kw", "energy_kwh", "traffic_index"]
TLS_KPIS = ["total_mwh", "annualized_mwh", "peak_kw", "mean_kw", "load_factor", "specific_kwh_m_year",
            "n_pollution_events", "n_accident_events"]
PYR_SERIES = ["S", "T", "P", "wv", "wc", "z"]


def rmse(a, b):
    if len(a) != len(b) or not b:
        return None, None
    n = len(b)
    e = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)) / n)
    mean = sum(b) / n
    rms = math.sqrt(sum(x * x for x in b) / n)
    negligible = abs(mean) <= 0.05 * rms if rms > 0 else True
    return e, (None if negligible else e / abs(mean))


def rel_err(x, ref):
    return None if ref is None or x is None or ref == 0 else abs(x - ref) / abs(ref)


def llm_values(answer):
    out = {}
    for v in (answer.get("parsed") or {}).get("values") or []:
        if isinstance(v, dict) and v.get("value") is not None:
            out[norm(v.get("field", ""))] = v["value"]
    return out


PYR_MODE = ("n", "mu", "sigma", "kappa")


def complete(case, answer):
    """The candidate gave every expected field; single-mode pyrcel references need the four mode parameters."""
    exp = expected(case)
    if case["domain"] == "pyrcel" and not all(k in exp for k in PYR_MODE):
        return False  # multi-mode reference (e.g. two aerosol modes): not replayable in this single-mode comparison
    got = llm_values(answer)
    return all(k in got for k in exp)


# ---------- backends: each run returns {"series": {name: (times, values)}, "scalars": {name: value}} ----------
def tls_run(values):
    sys.path.insert(0, str(REPO / "external/tunnel-load-simulator/src"))
    import pandas as pd
    from tunnel_load_simulator.simulator import TunnelConfig, run_monte_carlo
    cfg = TunnelConfig(**{k: values[k] for k in TunnelConfig.__dataclass_fields__})
    out = run_monte_carlo(cfg, pd.Timestamp(values["start_date"]), int(values["n_days"]), int(values["freq_minutes"]),
                          int(values["n_runs"]), int(values["base_seed"]))
    rep = out["representative"]
    times = [str(t) for t in rep["timestamp"]]
    series = {c: (times, [float(x) for x in rep[c]]) for c in TLS_SERIES}
    daily = rep.set_index("timestamp")["energy_kwh"].resample("1D").sum()
    series["daily_energy_kwh"] = ([str(t) for t in daily.index], [float(x) for x in daily])
    return {"series": series, "scalars": {k: float(out["kpis"][k].median()) for k in TLS_KPIS}}


def tls_configs(case, answer):
    ref_doc = json.loads((RESERVE / "tls" / case["reference_scenarios"][0]).read_text(encoding="utf-8"))["scenario"]
    ref = {k: v["value"] for g in ("inputs", "experiment") for k, v in ref_doc[g].items()}
    got = dict(ref)  # fields outside expected(): defaults accepted by the case itself
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = type(ref[k])(v) if isinstance(ref[k], (int, float)) and not isinstance(v, str) else v
    return ref, got, tls_run


def lql_run(x):
    sys.path.insert(0, str(REPO / "external/LQL-Equiv-web/src"))
    from lqlequiv import Course, Prescription, compute, load_library
    lib = load_library()
    plan = Prescription(courses=(Course(float(x["dose_per_fraction"]), float(x["n_fractions"])),),
                        reference_dose=float(x["reference_dose"]))
    res = compute(lib.organ(x["organ"]), lib.tumour_site(x["tumour_site"]), plan)
    c = res.courses[0]
    return {"series": {}, "scalars": {
        "bed_oar": c.bed_oar, "bed_tumour": c.bed_tumour, "eqd_oar_total": res.eqd_oar_total,
        "eqd_tumour_total": res.eqd_tumour_total, "ntcp_percent": res.ntcp_percent, "tcp_percent": res.tcp_percent,
        "cancer_risk": res.cancer_risk, "overall_days_oar": c.overall_days_oar, "overall_days_tumour": c.overall_days_tumour}}


def lql_configs(case, answer):
    exp = expected(case)
    got = dict(exp)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = v
    return exp, got, lql_run


def pyrcel_configs(case, answer):
    ref = case["reference"]
    exp = expected(case)
    got = dict(exp)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = float(v)

    def run(x):
        import pyrcel as pm
        aer = [pm.AerosolSpecies("a", pm.Lognorm(mu=x["mu"], sigma=x["sigma"], N=x["n"]), kappa=x["kappa"], bins=ref["bins"])]
        m = pm.ParcelModel(aer, V=x["v"], T0=x["t0"], S0=x["s0"], P0=x["p0"], accom=ref["accom"], console=False)
        o = m.run(t_end=ref["t_end"], output_dt=ref["output_dt"], terminate=ref["terminate"], terminate_depth=ref["terminate_depth"])
        frame, _ = o.to_pandas()
        times = [float(t) for t in o.time]
        series = {c: (times, [float(v) for v in frame[c]]) for c in PYR_SERIES}
        return {"series": series, "scalars": {"S_max": float(o.summary["S_max"]), "Nd": float(o.Nd), "nd_frac": float(o.nd_frac)}}
    return exp, got, run


def compare(ref_out, got_out):
    rows = []
    for name, (t_ref, v_ref) in ref_out["series"].items():
        t_got, v_got = got_out["series"][name]
        if t_got != t_ref:
            rows.append({"quantity": name, "kind": "series", "status": "support_differs"})
            continue
        e, ne = rmse(v_got, v_ref)
        rows.append({"quantity": name, "kind": "series", "status": "ok", "n": len(v_ref), "rmse": e, "nrmse": ne})
    for name, r in ref_out["scalars"].items():
        g = got_out["scalars"].get(name)
        ok = r is not None and g is not None
        rows.append({"quantity": name, "kind": "scalar", "status": "ok" if ok else "undefined_output",
                     "abs_err": abs(g - r) if ok else None, "rel_err": rel_err(g, r)})
    return rows


def main():
    model, domain = sys.argv[1], sys.argv[2]
    configs = {"tls": tls_configs, "lqlequiv": lql_configs, "pyrcel": pyrcel_configs}[domain]
    cases = {json.loads(line)["id"]: json.loads(line)
             for line in (RESERVE / domain / "pilot.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    rows, cache = [], {}
    for f in sorted((RESERVE / "runs" / "e1" / model).glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("domain") != domain or (a.get("parsed") or {}).get("decision") != "execute":
            continue
        c = cases.get(a["case_id"])
        if c is None or not expected(c) or (domain == "tls" and not c.get("reference_scenarios")):
            continue  # qualifier cases and cases without a numerical reference
        if c.get("variants") or c.get("modifications") or c.get("expected_turn_decisions"):
            continue  # E1 scores the first turn only; these references include later turns
        head = {"case_id": c["id"], "condition": a["condition"], "rep": a["rep"],
                "instructions": a.get("instructions_sha256_12", "v0")}
        if domain == "pyrcel" and not all(k in expected(c) for k in PYR_MODE):
            rows.append({**head, "quantity": "*", "status": "multi_mode_not_compared"})
            continue
        if not complete(c, a):
            rows.append({**head, "quantity": "*", "status": "incomplete_candidate"})
            continue
        ref_cfg, got_cfg, run = configs(c, a)
        key = json.dumps(ref_cfg, sort_keys=True, default=str)
        if key not in cache:
            cache[key] = run(ref_cfg)
        try:
            got_out = run(got_cfg)
        except Exception as exc:  # noqa: BLE001 - a backend rejection is an outcome
            rows.append({**head, "quantity": "*", "status": f"backend_error: {type(exc).__name__}"})
            continue
        rows += [{**head, **r} for r in compare(cache[key], got_out)]
    keys = ["case_id", "condition", "rep", "instructions", "quantity", "kind", "status", "n", "rmse", "nrmse", "abs_err", "rel_err"]
    with open(REPO / "evaluation" / "e1" / f"e1-numeric-{model}-{domain}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(domain, len(rows), "rows")


if __name__ == "__main__":
    main()
