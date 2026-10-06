"""Checks the gate, source integrity and an optional real CPU solve."""
import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from websemantic.adapters.pyrcel import run, verify_source
from websemantic.core.validation import Parameter, Scenario, validate

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    descriptor = yaml.safe_load((ROOT / "descriptors/pyrcel/descriptor.yaml").read_text(encoding="utf8"))
    doc = json.loads((ROOT / "examples/pyrcel-complete.json").read_text(encoding="utf8"))
    scenario = Scenario(doc["request"], doc["task"], **{g: {k: Parameter(**v) for k,v in doc[g].items()} for g in ("inputs", "experiment")})
    return scenario, descriptor


def test_complete_example_and_unit_semantics():
    scenario, descriptor = fixture()
    assert validate(scenario, descriptor).decision == "execute"
    assert descriptor["inputs"]["mu"]["unit"] == "unit:MicroM"
    assert "rayon" in descriptor["inputs"]["mu"]["definition"].lower()
    assert descriptor["inputs"]["S0"]["bounds"]["min_exclusive"] == -1


@pytest.mark.parametrize("name,value", [("V",0), ("S0",-1), ("sigma",1), ("N",-1), ("bins",2.5), ("T0",float("nan"))])
def test_invalid_physical_or_profile_values_refused_before_backend(tmp_path,name,value):
    scenario, descriptor = fixture()
    changed = dict(scenario.inputs)
    changed[name] = replace(changed[name], value=value)
    with pytest.raises(ValueError, match="Paramètres incomplets"):
        run(replace(scenario,inputs=changed),descriptor,tmp_path)


def test_unaccepted_assumption_does_not_run(tmp_path):
    scenario, descriptor = fixture()
    changed = dict(scenario.inputs)
    changed["N"] = replace(changed["N"], accepted=False)
    with pytest.raises(ValueError, match="unaccepted_assumption"):
        run(replace(scenario,inputs=changed),descriptor,tmp_path)


def test_reviewed_sources():
    backend=ROOT / "work/candidates/pyrcel"
    if not backend.exists():pytest.skip("Reviewed candidate checkout not installed")
    assert verify_source(backend)["commit"].startswith("977e909")


def test_changed_source_refused(tmp_path):
    (tmp_path / "pyrcel").mkdir()
    (tmp_path / "pyrcel/__init__.py").write_text("pass")
    with pytest.raises(ValueError,match="manquants"):
        verify_source(tmp_path)


@pytest.mark.skipif(importlib.util.find_spec("diffrax") is None, reason="Use the explicit pyrcel candidate environment for real solve")
def test_real_solve_preserves_native_times_and_traces(tmp_path):
    import numpy as np
    import pandas as pd
    scenario,descriptor=fixture()
    ex=dict(scenario.experiment)
    for name,value in (("t_end",30),("output_dt",5),("terminate","no")):
        ex[name]=replace(ex[name],value=value)
    inp=dict(scenario.inputs);inp["bins"]=replace(inp["bins"],value=10)
    scenario=replace(scenario,inputs=inp,experiment=ex)
    target,metrics=run(scenario,descriptor,ROOT,tmp_path)
    table=pd.read_csv(target / "trajectory.csv")
    assert np.array_equal(table.time_s.to_numpy(),np.arange(0,31,5))
    assert np.isfinite(table.to_numpy()).all()
    assert 0 <= metrics["activated_fraction"] <= 1
    assert metrics["actual_end_time_s"] == 30
    manifest=json.loads((target / "manifest.json").read_text(encoding="utf8"))
    assert manifest["execution"]["jax_backend"] == "cpu"
    assert manifest["execution"]["jax_enable_x64"] is True
    assert manifest["scenario"]["inputs"]["N"]["accepted"] is True
    assert manifest["output_qualification"]["wet_radii"]["all_radius_columns_unit"] == "m"


@pytest.mark.skipif(importlib.util.find_spec("diffrax") is None, reason="Explicit pyrcel environment required")
def test_real_activation_and_irregular_terminal_time(tmp_path):
    import numpy as np
    import pandas as pd
    scenario,descriptor=fixture()
    exp=dict(scenario.experiment);exp["output_dt"]=replace(exp["output_dt"],value=7)
    inputs=dict(scenario.inputs);inputs["bins"]=replace(inputs["bins"],value=10)
    target,metrics=run(replace(scenario,inputs=inputs,experiment=exp),descriptor,ROOT,tmp_path)
    table=pd.read_csv(target / "trajectory.csv")
    assert 0 < metrics["activated_number_cm3"] < 1100
    assert 0 < metrics["actual_end_time_s"] < 3000
    assert not np.isclose(np.diff(table.time_s)[-1],7)
    assert np.isclose(table.time_s.iloc[-1],metrics["actual_end_time_s"])
    assert np.isfinite(table.to_numpy()).all()


def test_source_digest_detects_mutation(tmp_path):
    import shutil
    backend=ROOT / "work/candidates/pyrcel"
    if not backend.exists():pytest.skip("Reviewed source not installed")
    shutil.copytree(backend / "pyrcel",tmp_path / "pyrcel")
    assert verify_source(tmp_path)["commit"].startswith("977e909")
    with (tmp_path / "pyrcel/model.py").open("a",encoding="utf8") as stream:stream.write("\n# modified\n")
    with pytest.raises(ValueError,match="Code pyrcel modifié"):
        verify_source(tmp_path)
