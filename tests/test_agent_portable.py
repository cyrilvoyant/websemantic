"""Web-materialized sources execute unchanged TLS without checkout metadata."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from websemantic.adapters.tls import run
from websemantic.registry import load_descriptor
from websemantic.replay import load_scenario

ROOT = Path(__file__).resolve().parents[1]


def materialize(target):
    index = json.loads((ROOT / "agent/files.json").read_text())
    for record in index["files"]:
        dest = target / record["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / record["path"], dest)
    shutil.copyfile(ROOT / "agent/files.json", target / "agent/files.json")
    return target


def test_web_files_match_native_execution_without_git(tmp_path):
    root = materialize(tmp_path / "web")
    assert not (root / "external/tunnel-load-simulator/.git").exists()
    process = subprocess.run([sys.executable, str(root / "agent/run_tls.py"),
                              str(root / "examples/tls-complete.json")],
                             capture_output=True, text=True, check=True)
    result = json.loads(process.stdout)
    portable = Path(result["result_directory"])
    scenario = load_scenario(json.loads((root / "examples/tls-complete.json").read_text()))
    native, medians = run(scenario, load_descriptor(ROOT, "tls"), ROOT, tmp_path / "native")
    assert result["median_indicators"] == medians
    for name in ("kpis", "representative", "daily", "envelope", "season_profiles"):
        pd.testing.assert_frame_equal(pd.read_csv(portable / f"{name}.csv"),
                                      pd.read_csv(native / f"{name}.csv"), check_exact=True)
    manifest = json.loads((portable / "manifest.json").read_text())
    assert manifest["source_verification"]["method"] == "sha256_lf"
    assert manifest["source_materialization"]["files"]


def test_changed_backend_refused_without_git(tmp_path):
    root = materialize(tmp_path)
    backend = root / "external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py"
    backend.write_bytes(backend.read_bytes() + b"\n# changed\n")
    scenario = load_scenario(json.loads((ROOT / "examples/tls-complete.json").read_text()))
    with pytest.raises(ValueError, match="Empreinte"):
        run(scenario, load_descriptor(ROOT, "tls"), root)
    assert not (root / "runs").exists()


def test_changed_contract_refused_before_execution(tmp_path):
    root = materialize(tmp_path)
    path = root / "ontology/tls-contract.json"
    path.write_bytes(path.read_bytes() + b" ")
    result = subprocess.run([sys.executable, str(root / "agent/run_tls.py"),
                             str(root / "examples/tls-complete.json")],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "Source incomplete or changed" in result.stderr
    assert not (root / "runs").exists()
