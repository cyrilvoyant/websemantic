"""Independent checks for candidate/support failures found during the E1 review."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_numeric():
    spec = importlib.util.spec_from_file_location(
        "review_numeric", ROOT / "evaluation/e1/numeric_e1.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "times,values,expected",
    [
        ([], [], "empty_or_misaligned_series"),
        ([0, 1], [1], "empty_or_misaligned_series"),
        ([0, 2], [1, 2], "support_differs"),
        ([0, 1], [1, float("nan")], "non_finite_values"),
    ],
)
def test_invalid_series_never_reports_success(times, values, expected):
    module = load_numeric()
    reference = {"series": {"power": ([0, 1], [1, 2])}, "scalars": {}}
    candidate = {"series": {"power": (times, values)}, "scalars": {}}
    result = module.compare(reference, candidate)
    assert result[0]["status"] == expected
    assert result[0].get("rmse") is None


def test_fractional_protocol_integer_is_not_truncated():
    module = load_numeric()
    answer = {"parsed": {"values": [{"field": "bins", "value": 2.5, "unit": "unit:NUM"}]}}
    assert module.candidate_issue(answer, {"domain": "pyrcel"}) == "non_integer_value:bins"


def test_missing_physical_unit_is_not_silently_accepted():
    module = load_numeric()
    answer = {"parsed": {"values": [{"field": "T0", "value": 283, "unit": None}]}}
    assert module.candidate_issue(answer, {"domain": "pyrcel"}) == "unit_missing:t0"
