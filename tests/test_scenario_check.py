"""SHACL check of LQL-Equiv scenarios before computing (web app 0.3.14)."""

from pathlib import Path

import pytest

pytest.importorskip("pyshacl")
from websemantic.scenario_check import check_lql, records  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLAN = dict(dose_per_fraction=3.0, n_fractions=20, gap_days=0.0)


def test_a_plausible_scenario_conforms():
    r = check_lql(ROOT, [PLAN], "Prostate", ["Rectum", "Bladder"], 2.0)
    assert r["status"] == "conforms" and r["records"] == 7 and r["messages"] == []
    assert r["engine"].startswith("pyshacl") and len(r["shapes_sha256"]) == 64


def test_each_course_is_one_group_instance():
    courses = [dict(dose_per_fraction=2.0, n_fractions=39, gap_days=10.0), PLAN]
    assert [rec[2] for rec in records(courses)] == ["course1"] * 3 + ["course2"] * 3
    assert check_lql(ROOT, courses, "Prostate", ["Rectum"])["status"] == "conforms"


def test_declared_bounds_are_enforced_and_named():
    r = check_lql(ROOT, [dict(dose_per_fraction=-2.0, n_fractions=0, gap_days=-1.0)], "Prostate", ["Rectum"], 0.0)
    assert r["status"] == "violation" and len(r["messages"]) == 4
    assert any(m.startswith("LQL_n_fractions = 0 (course1)") and "min 1" in m for m in r["messages"])


def test_a_stated_total_dose_is_checked_and_its_absence_is_said():
    plain = check_lql(ROOT, [dict(dose_per_fraction=2.0, n_fractions=39, gap_days=0.0)], "Prostate", ["Rectum"])
    assert plain["status"] == "conforms" and plain["relations_not_evaluated"]
    stated = check_lql(ROOT, [dict(dose_per_fraction=2.0, n_fractions=39, gap_days=0.0, total_dose=1.0)], "Prostate", ["Rectum"])
    assert stated["status"] == "violation" and stated["relations_not_evaluated"] == []
    assert any("total dose" in m for m in stated["messages"])
