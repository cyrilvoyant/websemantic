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


def invoke(root, document, *options):
    path = root / "study.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return subprocess.run([sys.executable, str(root / "agent/run_tls.py"), str(path), *map(str, options)],
                          capture_output=True, text=True, check=False)


def test_city_requires_context_before_run(tmp_path):
    root = materialize(tmp_path)
    document = json.loads((root / "examples/tls-complete.json").read_text())
    document["request"] += " Ajaccio."
    process = invoke(root, document)
    assert process.returncode != 0
    assert "fournir --context" in process.stderr
    assert not (root / "runs").exists()


def test_summer_followup_preserves_runs_and_traces_context(tmp_path):
    root = materialize(tmp_path)
    document = json.loads((root / "examples/tls-complete.json").read_text())
    first = invoke(root, document)
    assert first.returncode == 0, first.stderr
    previous = Path(json.loads(first.stdout)["result_directory"]) / "manifest.json"
    document["request"] += " Même tunnel à Ajaccio pour juillet 2025."
    document["experiment"]["start_date"]["value"] = "2025-07-01"
    document["experiment"]["n_days"]["value"] = 31
    context = root / "context.json"
    report = {"city": "Ajaccio", "summary": "Test fixture: sources unavailable; preserve accepted synthetic assumptions.",
              "sources": [{"url": "https://example.org/fixture", "retrieved_at": "2026-10-04", "status": "unavailable"}],
              "facts": [], "hypotheses": ["Existing fictitious tunnel profile"], "accepted": True}
    context.write_text(json.dumps(report), encoding="utf-8")
    process = invoke(root, document, "--context", context, "--previous", previous)
    assert process.returncode == 0, process.stderr
    target = Path(json.loads(process.stdout)["result_directory"])
    assert len(pd.read_csv(target / "representative.csv")) == 2976
    assert len(pd.read_csv(target / "daily.csv")) == 31
    assert len(pd.read_csv(target / "kpis.csv")) == 10
    manifest = json.loads((target / "manifest.json").read_text())
    assert {item["field"] for item in manifest["previous_study"]["changes"]} == {"experiment.start_date", "experiment.n_days"}
    assert json.loads((target / "geographical_context.json").read_text()) == report


def test_unaccepted_local_hypothesis_blocks(tmp_path):
    root = materialize(tmp_path)
    document = json.loads((root / "examples/tls-complete.json").read_text())
    report = {"city": "Ajaccio", "summary": "Fixture only", "sources": [{"url": "https://example.org/fixture",
              "retrieved_at": "2026-10-04", "status": "unavailable"}], "facts": [], "hypotheses": ["Unaccepted fixture"]}
    context = root / "context.json"
    context.write_text(json.dumps(report))
    process = invoke(root, document, "--place", "Ajaccio", "--context", context)
    assert process.returncode != 0
    assert "restent à accepter" in process.stderr
    assert not (root / "runs").exists()


def test_comparison_runs_without_git_or_yaml(tmp_path):
    root = materialize(tmp_path)
    document = json.loads((root / "examples/tls-complete.json").read_text())
    document["experiment"]["n_days"]["value"] = 1
    document["experiment"]["n_runs"]["value"] = 2
    second = json.loads(json.dumps(document))
    second["inputs"]["lighting_type"]["value"] = "sodium fixed"
    process = invoke(root, {"scenario_1": document, "scenario_2": second})
    assert process.returncode == 0, process.stderr
    target = Path(json.loads(process.stdout)["result_directory"])
    assert set(pd.read_csv(target / "kpis.csv")["scenario"]) == {"scenario_1", "scenario_2"}
    assert json.loads((target / "manifest.json").read_text())["status"] == "complete"
    assert (target / "comparison.json").exists()


def test_followup_rejects_implicit_change_of_realizations(tmp_path):
    root = materialize(tmp_path)
    document = json.loads((root / "examples/tls-complete.json").read_text())
    previous = root / "previous.json"
    previous.write_text(json.dumps({"scenario": document}))
    document["experiment"]["n_runs"]["value"] = 1
    process = invoke(root, document, "--previous", previous)
    assert process.returncode != 0
    assert "n_runs" in process.stderr
    assert not (root / "runs").exists()
