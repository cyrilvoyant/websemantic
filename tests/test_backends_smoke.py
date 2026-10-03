"""Smoke tests: the linked simulators still run, unmodified, through the pinned submodules."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "external" / "tunnel-load-simulator" / "src"))
sys.path.insert(0, str(ROOT / "external" / "LQL-Equiv-web" / "src"))


def test_tls_runs():
    pd = pytest.importorskip("pandas")
    from tunnel_load_simulator.simulator import TunnelConfig, run_monte_carlo

    cfg = TunnelConfig(
        length_m=2000, n_tubes=2, n_lanes_per_tube=2, altitude_m=200, max_depth_m=50,
        gradient_percent=1.0, tunnel_context="peri-urban", lighting_type="LED adaptive",
        ventilation_type="longitudinal", aux_kw_per_km_tube=10.0, base_fixed_kw=20.0,
        traffic_level=1.0, morning_peak_hour=8, evening_peak_hour=18, peak_width_h=1.5,
        traffic_sensitivity=0.5, noise_sigma=0.03, pollution_probability_per_day=0.02,
        accident_probability_per_day=0.01, pollution_sensitivity=0.3, accident_sensitivity=0.3,
    )
    out = run_monte_carlo(cfg, pd.Timestamp("2025-01-01"), 7, 60, 3, 42)
    assert set(out) == {"representative", "kpis", "envelope", "season_profiles"}
    assert len(out["kpis"]) == 3


def test_lqlequiv_reference_example():
    from lqlequiv import Course, Prescription, compute, load_library

    lib = load_library()
    plan = Prescription(courses=(Course(2.0, 39),), reference_dose=2.0)
    res = compute(lib.organ("Rectum"), lib.tumour_site("Prostate"), plan)
    assert round(res.eqd_oar_total, 2) == 78.0  # documented example in lqlequiv/__init__.py
