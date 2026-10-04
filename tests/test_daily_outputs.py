import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from websemantic.adapters.tls import run
from websemantic.session import Session

ROOT = Path(__file__).resolve().parents[1]


def test_annual_daily_series_preserves_native_energy(tmp_path):
    descriptor = yaml.safe_load((ROOT / "descriptors/tls/descriptor.yaml").read_text(encoding="utf-8"))
    session = Session(descriptor)
    session.propose_profile()
    session.accept_profile()
    session.set_value("experiment.n_days", "365")
    session.set_value("experiment.freq_minutes", "60")
    target, _ = run(session.scenario, descriptor, ROOT, tmp_path)
    daily = pd.read_csv(target / "daily.csv")
    native = pd.read_csv(target / "representative.csv")
    expected = native.assign(timestamp=pd.to_datetime(native.timestamp)).set_index("timestamp").resample("1D").agg({"energy_kwh": "sum", "power_kw": "mean"})
    assert len(daily) == 365 and len(native) == 8760
    np.testing.assert_allclose(daily.energy_kwh, expected.energy_kwh, rtol=1e-6)
    np.testing.assert_allclose(daily.mean_kw, expected.power_kw, rtol=1e-6)
    np.testing.assert_allclose(daily.energy_kwh.sum(), native.energy_kwh.sum(), rtol=1e-6)
    qualification = json.loads((target / "manifest.json").read_text(encoding="utf-8"))["output_qualification"]
    assert qualification["temporal_scope"]["native_step_minutes"] == 60
    assert qualification["tables"]["daily"]["columns"]["energy_kwh"]["unit"] == "kWh"
    assert "réalisation 0" in qualification["tables"]["daily"]["aggregation"]
