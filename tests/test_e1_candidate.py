"""Codex counter-examples: replay gate (no coercion; wrong, missing, unknown units get a status) and resume key."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "e1"))
import numeric_e1 as n
import run_e1

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
    ((("n_tubes", 2, "bananas"),), "unit_unverified"),      # unknown token on a dimensionless field
    ((("n_tubes", 2, "tubes"),), None),
    ((("aux_kw_per_km_tube", 35, "kW/(km·tube)"),), None),  # declared display unit / alias
    ((("aux_kw_per_km_tube", 35, "W"),), "unit_unverified"),
])
def test_candidate_issue(values, status):
    got = n.candidate_issue(answer(*values), CASE)
    assert (got is None) if status is None else (got or "").startswith(status)


def test_pyrcel_s0_unknown_unit():
    got = n.candidate_issue(answer(("S0", -0.02, "bananas")), {"domain": "pyrcel", "id": "y"})
    assert (got or "").startswith("unit_unverified")


def test_old_answer_without_request_hash_is_not_reused(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"context_sha256_12": "c", "instructions_sha256_12": "i", "request": "old request"}))
    assert run_e1.done(f, ("c", "i", run_e1.request_hash("old request")))
    assert not run_e1.done(f, ("c", "i", run_e1.request_hash("new request")))
    f.write_text(json.dumps({"context_sha256_12": "c", "instructions_sha256_12": "i"}))
    assert not run_e1.done(f, ("c", "i", "anything"))
