"""Contract tests for accepting, clarifying and rejecting candidate scenarios."""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from websemantic.core.validation import Parameter, Scenario, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def descriptor():
    return yaml.safe_load(
        (ROOT / "descriptors/tls/descriptor.yaml").read_text(encoding="utf-8")
    )


@pytest.fixture
def scenario(descriptor):
    values = {
        "length_m": 2000,
        "n_tubes": 2,
        "n_lanes_per_tube": 2,
        "altitude_m": 200,
        "max_depth_m": 50,
        "gradient_percent": 1.0,
        "tunnel_context": "peri-urban",
        "lighting_type": "LED adaptive",
        "ventilation_type": "longitudinal",
        "aux_kw_per_km_tube": 10,
        "base_fixed_kw": 20,
        "traffic_level": 1.0,
        "morning_peak_hour": 8,
        "evening_peak_hour": 18,
        "peak_width_h": 1.5,
        "traffic_sensitivity": 0.5,
        "noise_sigma": 0.03,
        "pollution_probability_per_day": 0.02,
        "accident_probability_per_day": 0.01,
        "pollution_sensitivity": 0.3,
        "accident_sensitivity": 0.3,
    }
    experiment = {
        "start_date": "2025-01-01",
        "n_days": 7,
        "freq_minutes": 60,
        "n_runs": 3,
        "base_seed": 42,
    }

    def records(group, data):
        return {
            k: Parameter(
                v,
                descriptor[group][k].get("unit"),
                "assumption",
                source="test fixture, not measured data",
                accepted=True,
            )
            for k, v in data.items()
        }

    return Scenario(
        "Fixture with explicitly accepted assumptions.",
        descriptor["tasks"]["supported"][0],
        records("inputs", values),
        records("experiment", experiment),
    )


def test_complete_scenario_executes_without_mutation(scenario, descriptor):
    before = dict(scenario.inputs)
    assert validate(scenario, descriptor).decision == "execute"
    assert scenario.inputs == before


@pytest.mark.parametrize(
    "name,value,code",
    [
        ("length_m", -1, "bounds"),
        ("n_tubes", 2.5, "type"),
        ("n_tubes", True, "type"),
        ("noise_sigma", float("nan"), "finite"),
        ("base_fixed_kw", float("inf"), "finite"),
        ("lighting_type", "invented LED", "category"),
    ],
)
def test_invalid_values_never_execute(scenario, descriptor, name, value, code):
    scenario.inputs[name] = replace(scenario.inputs[name], value=value)
    result = validate(scenario, descriptor)
    assert result.decision == "clarify"
    assert code in {i.code for i in result.issues}


def test_no_silent_completion(scenario, descriptor):
    scenario.inputs.pop("traffic_level")
    result = validate(scenario, descriptor)
    assert result.decision == "clarify"
    assert "traffic_level" not in scenario.inputs


def test_unaccepted_defaults_and_conflicts_block(scenario, descriptor):
    scenario.inputs["traffic_level"] = replace(
        scenario.inputs["traffic_level"], accepted=False
    )
    scenario.inputs["length_m"] = replace(
        scenario.inputs["length_m"], conflicts=(2000, 3000)
    )
    assert {"unaccepted_assumption", "conflict"} <= {
        i.code for i in validate(scenario, descriptor).issues
    }


def test_evidence_must_be_in_request(scenario, descriptor):
    scenario.inputs["length_m"] = Parameter(
        2000, "unit:M", "provided", evidence="a 2-km tunnel"
    )
    assert validate(scenario, descriptor).decision == "clarify"


def test_exact_evidence_span_is_accepted(scenario, descriptor):
    scenario = replace(scenario, request="A 2000 m tunnel.")
    scenario.inputs["length_m"] = Parameter(
        2000, "unit:M", "provided", evidence="2000 m"
    )
    assert validate(scenario, descriptor).decision == "execute"


@pytest.mark.parametrize("task", ["individual patient decision", "arbitrary task"])
def test_unknown_tasks_are_refused(scenario, descriptor, task):
    assert validate(replace(scenario, task=task), descriptor).decision == "refuse"


@pytest.mark.parametrize(
    "name,value",
    [
        ("n_days", 0),
        ("n_runs", 0),
        ("freq_minutes", -1),
        ("base_seed", -1),
        ("start_date", "2025-02-30"),
    ],
)
def test_invalid_experiments_block(scenario, descriptor, name, value):
    scenario.experiment[name] = replace(scenario.experiment[name], value=value)
    assert validate(scenario, descriptor).decision == "clarify"


def test_unknown_fields_and_noncanonical_units_block(scenario, descriptor):
    scenario.inputs["invented"] = Parameter(1)
    scenario.inputs["length_m"] = replace(
        scenario.inputs["length_m"], unit="unit:KiloM"
    )
    assert {"unknown_field", "unit"} <= {
        i.code for i in validate(scenario, descriptor).issues
    }
