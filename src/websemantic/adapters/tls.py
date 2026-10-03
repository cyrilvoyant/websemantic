"""Pinned, read-only TLS adapter with a validation gate at every run."""

import importlib.util
import json
import subprocess
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from websemantic.adapters.tls_outputs import qualify
from websemantic.core.validation import validate


def run(scenario, descriptor, workspace):
    result = validate(scenario, descriptor)
    if result.decision != "execute":
        raise ValueError("Configuration non validee : /show puis completer les champs.")
    config = {k: v.value for k, v in scenario.inputs.items()}
    exp = {k: v.value for k, v in scenario.experiment.items()}
    if exp["n_days"] > 366 or exp["n_runs"] > 30:
        raise ValueError("Limite PoC : 366 jours et 30 realisations maximum.")
    if exp["freq_minutes"] not in (5, 10, 15, 30, 60):
        raise ValueError("Pas temporel autorise : 5, 10, 15, 30, 60 minutes.")
    if exp["n_days"] * 1440 / exp["freq_minutes"] * exp["n_runs"] > 2_000_000:
        raise ValueError("Experience trop volumineuse pour ce PoC local.")
    nonnegative = (
        "max_depth_m",
        "gradient_percent",
        "aux_kw_per_km_tube",
        "base_fixed_kw",
        "traffic_level",
        "traffic_sensitivity",
        "pollution_sensitivity",
        "accident_sensitivity",
    )
    if config["peak_width_h"] <= 0 or any(config[k] < 0 for k in nonnegative):
        raise ValueError(
            "Largeur des pics positive et charges/sensibilites non negatives requises."
        )
    if any(not 0 <= config[k] < 24 for k in ("morning_peak_hour", "evening_peak_hour")):
        raise ValueError("Heures de pointe attendues entre 0 inclus et 24 exclu.")
    backend = Path(workspace) / "external/tunnel-load-simulator"
    commit = subprocess.run(
        ["git", "-C", str(backend), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if commit != descriptor["software"]["commit"]:
        raise ValueError("La revision TLS ne correspond pas au descripteur.")
    dirty = subprocess.run(
        ["git", "-C", str(backend), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if dirty:
        raise ValueError(
            "Le backend comporte des modifications suivies; execution refusee."
        )
    import pandas as pd

    spec = importlib.util.spec_from_file_location(
        "websemantic_pinned_tls", backend / "src/tunnel_load_simulator/simulator.py"
    )
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    outputs = module.run_monte_carlo(
        module.TunnelConfig(**config),
        pd.Timestamp(exp["start_date"]),
        exp["n_days"],
        exp["freq_minutes"],
        exp["n_runs"],
        exp["base_seed"],
    )
    qualification = qualify(outputs, exp)
    target = (
        Path(workspace)
        / "runs"
        / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:8]
        )
    )
    target.mkdir(parents=True)
    for name, table in outputs.items():
        table.to_csv(target / f"{name}.csv", index=False)
    manifest = {
        "software": descriptor["software"],
        "scenario": asdict(scenario),
        "nature": descriptor["nature"],
        "uncertainty": descriptor["uncertainty"],
        "validity_notes": descriptor["validity_notes"],
        "outputs": list(outputs),
        "output_qualification": qualification,
        "note": "Computational synthetic outputs, not field validation; JSON-LD not yet implemented.",
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    medians = (
        outputs["kpis"][["total_mwh", "annualized_mwh", "peak_kw", "load_factor", "specific_kwh_m_year"]]
        .median()
        .to_dict()
    )
    return target, medians
