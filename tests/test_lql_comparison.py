"""Scientific comparison gates and native fictitious execution."""

import copy
import csv
import json
from pathlib import Path

import pytest

from websemantic.lql_comparison import prepare, run, verdict
from websemantic.registry import load_descriptor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def document():
    return json.loads((ROOT / "examples/lql-comparison.json").read_text())


@pytest.mark.parametrize("left,right,expected", [
    ((80, 10), (70, 10), "left_dominates"),
    ((70, 10), (80, 10), "right_dominates"),
    ((80, 10), (70, 5), "tradeoff"),
    ((80, 10), (80, 10), "equivalent"),
    ((None, 10), (80, 10), "indeterminate"),
    ((80, float("nan")), (80, 10), "indeterminate"),
])
def test_probability_verdict(left, right, expected):
    def indicators(pair):
        return dict(zip(("tcp_percent", "ntcp_percent"), pair))
    assert verdict(indicators(left), indicators(right))["verdict"] == expected


@pytest.mark.parametrize("change", ["organ", "reference_dose", "unaccepted", "duplicate"])
def test_reject_before_calculation(document, change, monkeypatch, tmp_path):
    second = document["schedules"][1]
    if change == "duplicate":
        second["id"] = document["schedules"][0]["id"]
    elif change == "unaccepted":
        second["scenario"]["inputs"]["dose_per_fraction"]["accepted"] = False
    else:
        second["scenario"]["inputs"][change]["value"] = "Bladder" if change == "organ" else 3
    monkeypatch.setattr("websemantic.lql_comparison.execute", lambda *a: pytest.fail("premature run"))
    with pytest.raises(ValueError):
        run(document, load_descriptor(ROOT, "lql"), ROOT, tmp_path)
    assert not list(tmp_path.iterdir())


def test_group_expansion_does_not_choose_oar(document):
    original = copy.deepcopy(document)
    document["anatomical_group"] = {"value": "thoracic", "unit": None,
        "origin": "assumption", "source": "accepted fictitious group", "accepted": True}
    expanded = prepare(document, load_descriptor(ROOT, "lql"))
    assert len(expanded) == 6
    assert {s.inputs["organ"].value for _, _, s in expanded} == {"Rectum"}
    assert document["schedules"] == original["schedules"]
    del document["schedules"][0]["scenario"]["inputs"]["organ"]
    with pytest.raises(ValueError, match="organ"):
        prepare(document, load_descriptor(ROOT, "lql"))


def test_native_outputs_preserve_individual_runs(document, tmp_path):
    target, result = run(document, load_descriptor(ROOT, "lql"), ROOT, tmp_path)
    with (target / "indicators.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert float(rows[0]["physical_dose_gy"]) == 78
    assert float(rows[1]["physical_dose_gy"]) == 60
    manifest = json.loads((target / "manifest.json").read_text())
    for native in manifest["runs"]:
        assert (target / native["directory"] / "manifest.json").is_file()
        assert (target / native["directory"] / "semantics.ttl").is_file()
    assert len(result["comparisons"]) == 1
    assert manifest["request_document"] == document


def test_clinical_scope_and_unaccepted_target_selection_refused(document):
    descriptor = load_descriptor(ROOT, "lql")
    document["schedules"][1]["scenario"]["experiment"]["scenario_scope"]["value"] = "patient"
    with pytest.raises(ValueError):
        prepare(document, descriptor)
    document["schedules"][1]["scenario"]["experiment"]["scenario_scope"]["value"] = "fictitious"
    document["targets"] = {"value": ["Prostate"], "unit": None, "origin": "assumption",
                           "source": "proposed targets", "accepted": False}
    with pytest.raises(ValueError, match="acceptance"):
        prepare(document, descriptor)
