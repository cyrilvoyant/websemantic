"""Actual pinned LQL calculation and contract refusal checks."""

import csv
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from websemantic.adapters import lql
from websemantic.core.validation import Parameter, Scenario, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def descriptor():
    return yaml.safe_load((ROOT / "descriptors/lqlequiv/descriptor.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def scenario():
    data = json.loads((ROOT / "examples/lql-complete.json").read_text(encoding="utf-8"))
    return Scenario(data["request"], data["task"],
                    {name: Parameter(**item) for name, item in data["inputs"].items()},
                    {name: Parameter(**item) for name, item in data["experiment"].items()})


def modified(scenario, **values):
    return replace(scenario, inputs={**scenario.inputs, **{
        name: replace(scenario.inputs[name], value=value) for name, value in values.items()
    }})


def test_native_reference_and_traced_outputs(descriptor, scenario, tmp_path):
    assert validate(scenario, descriptor).decision == "execute"
    target, indicators = lql.run(scenario, descriptor, ROOT, tmp_path)
    assert indicators["physical_dose_gy"] == 78
    assert indicators["eqd_oar_total"] == pytest.approx(78)
    assert indicators["eqd_tumour_total"] == pytest.approx(78)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_verification"]["files"] == lql.EXPECTED_FILES
    assert manifest["tissues"]["organ"]["name"] == "Rectum"
    assert manifest["backend_options"]["reproduce_2014"] is False
    assert (target / "semantics.ttl").is_file()
    with (target / "indicators.csv").open(encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 1


def test_deterministic_backend(descriptor, scenario, tmp_path):
    _, first = lql.run(scenario, descriptor, ROOT, tmp_path)
    _, second = lql.run(scenario, descriptor, ROOT, tmp_path)
    assert first == second


@pytest.mark.parametrize("values", [
    {"n_fractions": 39.5}, {"n_fractions": 0}, {"dose_per_fraction": -1},
    {"dose_per_fraction": float("nan")}, {"reference_dose": 0}, {"gap_days": -1},
    {"organ": "unknown"}, {"tumour_site": "unknown"}, {"bifractionated": True},
])
def test_bad_inputs_refused_before_backend(descriptor, scenario, tmp_path, values):
    with patch.object(lql, "_backend", side_effect=AssertionError("backend must not run")), pytest.raises(ValueError):
        lql.run(modified(scenario, **values), descriptor, ROOT, tmp_path)


def test_unaccepted_defaults_and_clinical_task_refused(descriptor, scenario, tmp_path):
    unaccepted = replace(scenario, inputs={**scenario.inputs,
        "reference_dose": replace(scenario.inputs["reference_dose"], accepted=False)})
    for case in (unaccepted, replace(scenario, task="clinical dose prescription"),
                 replace(scenario, experiment={"scenario_scope": Parameter("patient", None, "assumption", source="case", accepted=True)})):
        with pytest.raises(ValueError):
            lql.run(case, descriptor, ROOT, tmp_path)


def test_descriptor_revision_refused(descriptor, scenario, tmp_path):
    descriptor["software"]["commit"] = "different"
    with pytest.raises(ValueError, match="Révision"):
        lql.run(scenario, descriptor, ROOT, tmp_path)


def test_source_tampering_refused_without_touching_upstream(descriptor, scenario, tmp_path):
    source = Path.read_bytes
    def altered(path):
        result = source(path)
        return result + b"# altered\n" if path.name == "model.py" else result
    with patch.object(Path, "read_bytes", altered), pytest.raises(ValueError, match="Empreinte"):
        lql.run(scenario, descriptor, ROOT, tmp_path)


def test_native_invalid_eqd_is_not_reported(descriptor, scenario, tmp_path):
    # Above the LQL transition, bifractionation's repair correction is undefined.
    target, indicators = lql.run(modified(scenario, dose_per_fraction=20., bifractionated="yes"), descriptor, ROOT, tmp_path)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["flags"]["oar_total_valid"] is False
    assert indicators["eqd_oar_total"] is None
    assert indicators["ntcp_percent"] is None
    assert indicators["physical_dose_gy"] == 780
    with (target / "indicators.csv").open(encoding="utf-8") as handle:
        assert next(csv.DictReader(handle))["eqd_oar_total"] == ""


def test_library_categories_exact(descriptor):
    module = lql._backend(ROOT, descriptor)
    assert descriptor["inputs"]["organ"]["values"] == module.load_library().organ_names
    assert descriptor["inputs"]["tumour_site"]["values"] == module.load_library().tumour_names


def test_saturated_native_root_is_suppressed(descriptor, scenario, tmp_path):
    target, indicators = lql.run(modified(scenario, n_fractions=1000), descriptor, ROOT, tmp_path)
    flags = json.loads((target / "manifest.json").read_text(encoding="utf-8"))["flags"]
    assert flags["oar_saturated"] is True
    assert flags["oar_total_valid"] is True
    assert indicators["eqd_oar_total"] is None
    assert indicators["ntcp_percent"] is None
    assert indicators["physical_dose_gy"] == 2000


def test_hypofractionated_result_matches_native_not_physical_proxy(descriptor, scenario, tmp_path):
    module = lql._backend(ROOT, descriptor)
    expected = module.compute("Rectum", "Prostate", module.Prescription((module.Course(3., 20),)))
    _, indicators = lql.run(modified(scenario, dose_per_fraction=3., n_fractions=20), descriptor, ROOT, tmp_path)
    assert indicators["eqd_oar_total"] == expected.eqd_oar_total
    assert indicators["eqd_tumour_total"] == expected.eqd_tumour_total
    assert indicators["physical_dose_gy"] == 60
    assert indicators["bed_oar"] != indicators["physical_dose_gy"]
