import json
from pathlib import Path

import pytest
import yaml

from websemantic.adapters.tls import run
from websemantic.session import ClarificationNeeded, Session

ROOT = Path(__file__).resolve().parents[1]


def test_comparison_preserves_existing_scenario(session):
    session.propose_profile()
    session.accept_profile()
    before = session.scenario
    with pytest.raises(ClarificationNeeded):
        session.apply("1km fort ou 2km faible", {
            "task": session.descriptor["tasks"]["supported"][1], "updates": [],
        })
    assert session.scenario is before
    assert session.pending_clarification
    assert session.history[-1]["user"] == "1km fort ou 2km faible"


def test_duplicate_values_request_clarification(session):
    update = {"field": "inputs.length_m", "value": "1000", "unit": "unit:M", "evidence": "1km"}
    with pytest.raises(ClarificationNeeded):
        session.apply("1km ou 2km", {"task": session.scenario.task, "updates": [update, update]})
    assert not session.scenario.inputs
    session.apply("un seul tunnel", {"task": session.scenario.task, "updates": []})
    assert session.pending_clarification is None


@pytest.fixture
def session():
    return Session(
        yaml.safe_load(
            (ROOT / "descriptors/tls/descriptor.yaml").read_text(encoding="utf-8")
        )
    )


def test_profile_requires_acceptance(session):
    session.propose_profile()
    assert session.result().decision == "clarify"
    session.accept_profile()
    assert session.result().decision == "execute"


def test_bad_extraction_is_atomic(session):
    parsed = {
        "task": session.scenario.task,
        "updates": [
            {
                "field": "inputs.length_m",
                "value": "2000",
                "unit": "unit:M",
                "evidence": "2000 m",
            },
            {
                "field": "inputs.n_tubes",
                "value": "2",
                "unit": "unit:NUM",
                "evidence": "invented",
            },
        ],
    }
    with pytest.raises(ValueError):
        session.apply("2000 m", parsed)
    assert not session.scenario.inputs


def test_kilometres_and_profile_preserve_extracted_values(session):
    session.apply(
        "Un tunnel de 2 km",
        {
            "task": session.scenario.task,
            "updates": [
                {
                    "field": "inputs.length_m",
                    "value": "2",
                    "unit": "km",
                    "evidence": "2 km",
                }
            ],
        },
    )
    session.propose_profile()
    session.accept_profile()
    assert session.scenario.inputs["length_m"].value == 2000
    assert "x 1000" in session.scenario.inputs["length_m"].source


def test_backend_gate_blocks_before_execution(session, tmp_path):
    with pytest.raises(ValueError, match="non validee"):
        run(session.scenario, session.descriptor, tmp_path)


def test_local_run_records_configuration(session):
    session.propose_profile()
    session.accept_profile()
    target, medians = run(session.scenario, session.descriptor, ROOT)
    assert medians["total_mwh"] > 0
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["software"]["commit"] == session.descriptor["software"]["commit"]
    assert manifest["scenario"]["inputs"]["traffic_level"]["accepted"]


def test_wrong_llm_length_unit_cannot_multiply_metres(session):
    session.apply(
        "Longueur 2000 m",
        {
            "task": session.scenario.task,
            "updates": [
                {
                    "field": "inputs.length_m",
                    "value": "2000",
                    "unit": "km",
                    "evidence": "2000 m",
                }
            ],
        },
    )
    assert session.scenario.inputs["length_m"].value == 2000
