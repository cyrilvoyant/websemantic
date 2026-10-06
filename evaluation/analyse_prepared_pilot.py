"""Summarise observed CLI outcomes; compare executed TLS cases to frozen references.

No inferred success label for incomplete or unsupported workflows. Private case
data and numerical outputs are not copied into the public summary.
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from websemantic.registry import load_descriptor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/prepared-pilot-20261006"
CORPUS = ROOT.parent / "benchmark-reserve"


def equal(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return bool(np.isclose(a, b, rtol=0, atol=1e-10))
    return a == b


def metric(actual, reference):
    a, b = np.asarray(actual, dtype=float), np.asarray(reference, dtype=float)
    assert a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    rmsd = float(np.sqrt(np.mean((a - b) ** 2)))
    denominator = float(np.sqrt(np.mean(b ** 2)))
    return {"n": a.size, "rmsd": rmsd, "nrmsd": rmsd / denominator if denominator else None}


def native_tls(trial, run):
    paths = trial["expected"].get("reference_scenarios", [])
    if len(paths) != 1:
        return {"status": "no unique frozen configuration"}
    reference = json.loads((CORPUS / "tls" / paths[0]).read_text(encoding="utf-8"))["scenario"]
    target = Path(run["path"])
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    actual = manifest["scenario"]
    fields = [(g, k) for g in ("inputs", "experiment") for k in reference[g]]
    mismatches = [f"{g}.{k}" for g, k in fields if
                  k not in actual[g] or not equal(actual[g][k]["value"], reference[g][k]["value"])
                  or actual[g][k]["unit"] != reference[g][k]["unit"]]
    if mismatches:
        return {"status": "configuration differs from reference", "mismatches": mismatches}
    module_path = ROOT / "external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py"
    spec = importlib.util.spec_from_file_location("prepared_native_tls", module_path)
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    spec.loader.exec_module(backend)
    values = {g: {k: v["value"] for k, v in reference[g].items()} for g in ("inputs", "experiment")}
    exp = values["experiment"]
    native = backend.run_monte_carlo(backend.TunnelConfig(**values["inputs"]),
        pd.Timestamp(exp["start_date"]), exp["n_days"], exp["freq_minutes"], exp["n_runs"], exp["base_seed"])
    frame = pd.read_csv(target / "representative.csv")
    assert np.array_equal(pd.to_datetime(frame["timestamp"]), pd.to_datetime(native["representative"]["timestamp"]))
    pairs = {name: metric(frame[name], native["representative"][name]) for name in ("power_kw", "energy_kwh")}
    native["representative"].to_csv(target / "frozen_native_reference.csv", index=False)
    return {"status": "compared", "canonical_fields_matched": len(fields), "metrics": pairs}


def main():
    index = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
    details, summary = [], {}
    for row in index["results"]:
        target = Path(row["path"])
        trial = json.loads((target / "trial.json").read_text(encoding="utf-8"))
        transcript = (target / "transcript.txt").read_text(encoding="utf-8")
        domain = row["domain"]
        aggregate = summary.setdefault(domain, {"cases": 0, "extraction_calls": 0, "cases_with_runs": 0,
            "runs": 0, "extract_access_errors": 0, "consent_block_messages": 0,
            "comparison_unavailable_messages": 0, "explicit_fields_correct": 0,
            "explicit_fields_checked": 0, "unit_fields_correct": 0})
        aggregate["cases"] += 1
        aggregate["extraction_calls"] += len(trial["calls"])
        aggregate["cases_with_runs"] += bool(trial["runs"])
        aggregate["runs"] += len(trial["runs"])
        aggregate["extract_access_errors"] += sum("error" in c for c in trial["calls"])
        aggregate["consent_block_messages"] += transcript.count("Les hypothèses restent non acceptées.")
        aggregate["comparison_unavailable_messages"] += transcript.count("La comparaison n’est pas disponible")
        detail = {"id": row["id"], "fields": [], "numerical": []}
        expected = trial["expected"].get("expected_fields", {})
        continuation = trial["expected"].get("continuation", {})
        if continuation.get("steps") and len(trial["continuation_steps_done"]) == len(continuation["steps"]):
            expected = {**expected, **continuation.get("expected_fields", {})}
        descriptor = load_descriptor(ROOT, "lql" if domain == "lqlequiv" else domain)
        for field, expected_value in expected.items():
            group, name = field.split(".", 1)
            scenarios = list(trial.get("final_comparison", {}).values()) or [trial.get("final_scenario", {})]
            records = [scenario.get(group, {}).get(name, {}) for scenario in scenarios]
            correct = all(equal(record.get("value"), expected_value) for record in records)
            unit_correct = all(bool(record) and record.get("unit") == descriptor[group][name].get("unit")
                               for record in records)
            aggregate["explicit_fields_checked"] += 1
            aggregate["explicit_fields_correct"] += correct
            aggregate["unit_fields_correct"] += unit_correct
            detail["fields"].append({"field": field, "correct": correct, "unit_correct": unit_correct})
        if domain == "tls":
            detail["numerical"] = [native_tls(trial, run) for run in trial["runs"]]
        details.append(detail)
    report = {"scope": "One development repetition through dedicated CLI; not multi-provider or document ablation",
              "model_requested": index["model_requested"], "domains": summary,
              "completed_cases": len(details), "stopped_on_access_error": index["stopped_on_access_error"],
              "extraction_calls_only": True,
              "limits": ["Web/geographic research calls are not included in extraction-call counts.",
                         "Cases with outputs are not automatically task successes.",
                         "Field accuracy covers only corpus explicit expected_fields, not all outputs or all domains.",
                         "Some reference tasks exceed the implemented single-course/single-mode profiles.",
                         "No confirmatory success rate, ontology LLM effect or provider comparison is estimated."]}
    numerical = [n for d in details for n in d["numerical"] if n["status"] == "compared"]
    report["numerical"] = {"reference_matched_cases": len(numerical),
        "vectors": sum(len(n["metrics"]) for n in numerical),
        "maximum_nrmsd": max((m["nrmsd"] for n in numerical for m in n["metrics"].values()), default=None)}
    (OUT / "scoring.json").write_text(json.dumps({"summary": report, "cases": details}, indent=2), encoding="utf-8")
    (ROOT / "evaluation/prepared-pilot-20261006.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
