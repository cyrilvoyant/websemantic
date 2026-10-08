"""Published-file closure and acceptance typing at the execution boundary."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from websemantic.core.validation import validate
from websemantic.registry import load_descriptor
from websemantic.replay import load_scenario

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("model,field", [("tls", "length_m"), ("lql", "dose_per_fraction"), ("pyrcel", "V")])
@pytest.mark.parametrize("acceptance", ["false", "true", 1, 0, None])
def test_gate_rejects_non_boolean_acceptance(model, field, acceptance):
    scenario = load_scenario(json.loads((ROOT / f"examples/{model}-complete.json").read_text()))
    changed = replace(scenario, inputs={**scenario.inputs,
                                       field: replace(scenario.inputs[field], accepted=acceptance)})
    result = validate(changed, load_descriptor(ROOT, model))
    assert result.decision != "execute"
    assert any(i.code == "acceptance_type" and i.field == "inputs." + field for i in result.issues)


@pytest.mark.parametrize("example", ["lql-complete", "lql-comparison"])
def test_lql_common_entry_from_published_files(tmp_path, example):
    index = json.loads((ROOT / "agent/files-lql.json").read_text())
    for record in index["files"]:
        dest = tmp_path / record["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / record["path"], dest)
    shutil.copyfile(ROOT / "agent/files-lql.json", tmp_path / "agent/files-lql.json")
    scenario_path = tmp_path / f"examples/{example}.json"
    result = subprocess.run([sys.executable, str(tmp_path / "agent/run.py"), "lql", str(scenario_path)],
                            capture_output=True, text=True, check=True)
    response = json.loads(result.stdout)
    if example == "lql-complete":
        assert response["indicators"]["physical_dose_gy"] == 78
        assert response["indicators"]["eqd_oar_total"] == 78
    else:
        assert response["indicators"]["comparisons"][0]["verdict"] == "tradeoff"
        assert (Path(response["result_directory"]) / "comparisons.csv").is_file()
    manifest = json.loads(Path(response["manifest"]).read_text())
    assert manifest["source_materialization"]["files"] == index["files"]
    assert not any(tmp_path.rglob(".git"))


def test_pyrcel_index_contains_imported_atmosphere_data():
    index = json.loads((ROOT / "agent/files-pyrcel.json").read_text())
    assert "external/pyrcel/pyrcel/data/std_atm.csv" in {r["path"] for r in index["files"]}
