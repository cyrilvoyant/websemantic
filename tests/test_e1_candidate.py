"""Codex counter-examples for the replay gate: no coercion, wrong/missing/unverifiable units get an explicit status."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "e1"))
import numeric_e1 as n  # noqa: E402

CASE = {"domain": "tls", "id": "x"}


def answer(*values):
    return {"parsed": {"values": [dict(zip(("field", "value", "unit"), v)) for v in values]}}


@pytest.mark.parametrize(("values", "status"), [
    ((("length_m", 2000, "m"),), None),
    ((("length_m", 2000, ""),), "unit_missing"),
    ((("length_m", 2, "km"),), "unit_mismatch"),
    ((("n_tubes", 2.5, ""),), "non_integer_value"),
    ((("n_runs", 2.5, ""),), "non_integer_value"),          # not an expected field: still checked
    ((("n_tubes", "deux", ""),), "non_integer_value"),
    ((("n_tubes", 2, "m"),), "unit_mismatch"),              # dimensionless field given a physical unit
    ((("aux_kw_per_km_tube", 35, "kW/(km·tube)"),), None),  # declared display unit / alias
    ((("aux_kw_per_km_tube", 35, "W"),), "unit_unverified"),
])
def test_candidate_issue(values, status):
    got = n.candidate_issue(answer(*values), CASE)
    assert (got is None) if status is None else (got or "").startswith(status)
