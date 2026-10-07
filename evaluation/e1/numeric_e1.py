"""Numerical consequence of each E1 interpretation, for every output quantity.

Numerical consequence WITH CONTROLLED COMPLETION: replay only when the candidate itself
supplied every expected field; fields outside the expected set (defaults the case accepts,
protocol settings) come from the case scenario and are listed in the "completed_from_case"
column. This is the consequence of the candidate's interpretation, not an autonomous
conforming execution. Values are not coerced: a non-integer for an integer field or a unit
different from the canonical unit gives an explicit status. Every output is compared:
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
    if len(a) != len(b) or not b or not all(map(math.isfinite, a)) or not all(map(math.isfinite, b)):
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


INT_FIELDS = {"n_tubes", "n_lanes_per_tube", "n_days", "freq_minutes", "n_runs", "base_seed", "n_fractions", "bins"}
UNIT_ALIASES = {"unit:M": {"m", "unit:m", "metre", "mètre", "meters", "metres", "mètres"},
                "unit:KiloW": {"kw", "kilow", "kilowatt", "kilowatts", "unit:kilow"}, "unit:GRAY": {"gy", "unit:gray", "gray"},
                "unit:K": {"k", "unit:k", "kelvin"}, "unit:PA": {"pa", "unit:pa"},
                "unit:M-PER-SEC": {"m/s", "unit:m-per-sec"}, "unit:MicroM": {"µm", "μm", "um", "microm", "unit:microm", "micrometre", "micron", "microns"},
                "unit:PER-CentiM3": {"cm-3", "cm⁻³", "/cm3", "cm^-3", "unit:per-centim3", "per cm3"},
                "unit:DAY": {"d", "day", "days", "jour", "jours", "unit:day"}, "unit:MIN": {"min", "minute", "minutes", "unit:min"},
                "unit:HR": {"h", "hour", "hours", "heure", "heures", "unit:hr"}, "unit:PERCENT": {"%", "percent", "unit:percent"},
                "unit:SEC": {"s", "sec", "second", "seconds", "seconde", "secondes", "unit:sec"}}
DIMENSIONLESS = {"unit:UNITLESS", "unit:NUM"}
PHYSICAL_TOKENS = set().union(*UNIT_ALIASES.values())   # a dimensionless field given in one of these is a unit error


def candidate_issue(answer, case):
    """Explicit status if a candidate value would need coercion or carries a wrong, missing or unverifiable unit.
    Checked for every field the candidate gives, expected or not."""
    import yaml
    d = yaml.safe_load((REPO / "descriptors" / case["domain"] / "descriptor.yaml").read_text(encoding="utf-8"))
    specs = {norm(n): sp for g in ("inputs", "experiment") for n, sp in (d.get(g) or {}).items()}
    units = {k: sp.get("unit") for k, sp in specs.items()}
    for v in (answer.get("parsed") or {}).get("values") or []:
        if not isinstance(v, dict) or v.get("value") is None:
            continue
        k, x = norm(v.get("field", "")), v["value"]
        if k in INT_FIELDS and (isinstance(x, bool) or not isinstance(x, (int, float)) or not float(x).is_integer()):
            return f"non_integer_value:{k}"
        canon, given = units.get(k), str(v.get("unit") or "").strip().lower()
        if not canon:
            continue
        official = {canon.lower(), canon.split(":", 1)[-1].lower(), str(specs[k].get("display_unit") or "").lower()} | \
            {str(a).lower() for a in specs[k].get("unit_aliases") or []}
        if canon in DIMENSIONLESS:
            if given in PHYSICAL_TOKENS - {""}:
                return f"unit_mismatch:{k}:{given}"
        elif not given:
            return f"unit_missing:{k}"
        elif canon in UNIT_ALIASES:
            if given not in UNIT_ALIASES[canon] and given not in official:
                return f"unit_mismatch:{k}:{given}"
        elif given not in official:
            return f"unit_unverified:{k}:{given}"
    return None


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
    got = dict(ref)  # fields outside expected(): defaults accepted by the case itself (controlled completion)
    for k, v in llm_values(answer).items():
        if k in got:
            got[k] = int(v) if isinstance(ref[k], int) and not isinstance(ref[k], bool) and float(v).is_integer() else v
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

    proto = {k: ref[k] for k in ("bins", "accom", "t_end", "output_dt", "terminate", "terminate_depth")}
    cand = llm_values(answer)
    got_proto = {k: cand.get(k, proto[k]) for k in proto}  # candidate settings are used, divergences are measured
    exp = dict(exp, _proto=proto)
    got = dict(got, _proto=got_proto)

    def run(x):
        import pyrcel as pm
        pr = x["_proto"]
        aer = [pm.AerosolSpecies("a", pm.Lognorm(mu=x["mu"], sigma=x["sigma"], N=x["n"]), kappa=x["kappa"], bins=int(pr["bins"]))]
        m = pm.ParcelModel(aer, V=x["v"], T0=x["t0"], S0=x["s0"], P0=x["p0"], accom=pr["accom"], console=False)
        o = m.run(t_end=pr["t_end"], output_dt=pr["output_dt"], terminate=bool(pr["terminate"]), terminate_depth=pr["terminate_depth"])
        frame, _ = o.to_pandas()
        times = [float(t) for t in o.time]
        series = {c: (times, [float(v) for v in frame[c]]) for c in PYR_SERIES}
        return {"series": series, "scalars": {"S_max": float(o.summary["S_max"]), "Nd": float(o.Nd), "nd_frac": float(o.nd_frac)}}
    return exp, got, run


def compare(ref_out, got_out):
    rows = []
    for name, (t_ref, v_ref) in ref_out["series"].items():
        t_got, v_got = got_out["series"][name]
        if not (len(t_ref) == len(v_ref) > 0 and len(t_got) == len(v_got) > 0):
            rows.append({"quantity": name, "kind": "series", "status": "empty_or_misaligned_series"})
            continue
        if t_got != t_ref:
            rows.append({"quantity": name, "kind": "series", "status": "support_differs", "n": len(v_ref)})
            continue
        e, ne = rmse(v_got, v_ref)
        if e is None:
            rows.append({"quantity": name, "kind": "series", "status": "non_finite_values", "n": len(v_ref)})
            continue
        rows.append({"quantity": name, "kind": "series", "status": "ok", "n": len(v_ref), "rmse": e, "nrmse": ne})
    period_differs = any(r.get("status") == "support_differs" for r in rows)
    for name, r in ref_out["scalars"].items():
        g = got_out["scalars"].get(name)
        ok = r is not None and g is not None
        status = "period_differs" if period_differs else ("ok" if ok else "undefined_output")
        rows.append({"quantity": name, "kind": "scalar", "status": status,
                     "abs_err": abs(g - r) if ok else None, "rel_err": rel_err(g, r) if ok else None})
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
        issue = candidate_issue(a, c)
        if issue:
            rows.append({**head, "quantity": "*", "status": issue})
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
        filled = sorted(k for k in (ref_cfg if isinstance(ref_cfg, dict) else {}) if k not in llm_values(a) and not k.startswith("_"))
        rows += [{**head, "completed_from_case": " ".join(filled), **r} for r in compare(cache[key], got_out)]
    keys = ["case_id", "condition", "rep", "instructions", "quantity", "kind", "status", "n", "rmse", "nrmse", "abs_err", "rel_err",
            "completed_from_case"]
    with open(REPO / "evaluation" / "e1" / f"e1-numeric-{model}-{domain}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(domain, len(rows), "rows")


if __name__ == "__main__":
    main()
