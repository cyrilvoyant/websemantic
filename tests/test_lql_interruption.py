"""Biologically equivalent resumption of an interrupted fictitious schedule (unchanged LQL-Equiv library).

Every EQD2 checked here is recomputed with the library itself; the search only chooses the doses to try.
"""

import math
from pathlib import Path

import pytest
import yaml

from websemantic.lql_interruption import RESOLUTION_GY, Situation, _iso_dose, _Model, check, resume

ROOT = Path(__file__).resolve().parents[1]
DESC = yaml.safe_load((ROOT / "descriptors" / "lqlequiv" / "descriptor.yaml").read_text(encoding="utf-8"))
ORGANS = ("Rectum", "Small bowel", "Bladder")
BASE = dict(tumour="Prostate", organs=ORGANS, planned_dose=3.0, planned_sessions=10, done_sessions=2,
            gap_days=10, max_remaining=5)


def run(**changes):
    s = Situation(**{**BASE, **changes})
    return s, resume(s, ROOT, DESC)


def eqd2(s, organ, dose, n):
    return _Model(ROOT, DESC, s).eqd2(organ, [(s.planned_dose, s.done_sessions, 0.0), (dose, n, s.gap_days)])


# ------------------------------------------------------------ equivalence, recomputed with the library


def test_tumour_equivalence_is_reached_at_the_first_grid_dose():
    s, r = run()
    target = r["planned"]["tumour_eqd2"]
    for row in r["equivalent"]:
        t = row["tumour"]
        if t["dose_per_session"] is None:
            continue
        d, n = t["dose_per_session"], row["sessions"]
        assert eqd2(s, "Rectum", d, n)[0] == t["obtained_eqd2"] >= target == t["target_eqd2"]
        assert t["difference_gy"] == pytest.approx(t["obtained_eqd2"] - target)
        assert eqd2(s, "Rectum", round(d - RESOLUTION_GY, 2), n)[0] < target


def test_each_organ_equivalence_is_reached_at_the_first_grid_dose():
    s, r = run()
    row = r["equivalent"][-1]
    for organ in ORGANS:
        e = row["organs"][organ]["equivalent"]
        assert eqd2(s, organ, e["dose_per_session"], row["sessions"])[1] >= r["planned"]["organs_eqd2"][organ]
        assert eqd2(s, organ, round(e["dose_per_session"] - 0.01, 2), row["sessions"])[1] < e["target_eqd2"]


def test_no_interruption_gives_back_the_planned_dose():
    _, r = run(gap_days=0, max_remaining=8)
    row = r["equivalent"][-1]
    assert row["sessions"] == 8 and row["tumour"]["dose_per_session"] == pytest.approx(3.0, abs=0.02)
    assert all(v["equivalent"]["dose_per_session"] == pytest.approx(3.0, abs=0.02) for v in row["organs"].values())


def test_fewer_sessions_need_a_higher_dose_per_session():
    _, r = run()
    doses = [row["tumour"]["dose_per_session"] for row in r["equivalent"] if row["tumour"]["dose_per_session"]]
    assert doses == sorted(doses, reverse=True) and len(set(doses)) == len(doses)


def test_a_longer_interruption_needs_more_dose_for_the_tumour():
    _, short = run(gap_days=5)
    _, long = run(gap_days=30)
    assert long["with_all_remaining_sessions"]["tumour"] > short["with_all_remaining_sessions"]["tumour"]


def test_uncompensated_resumption_loses_tumour_effect():
    _, r = run()
    assert r["uncompensated"]["sessions"] == 5 and r["uncompensated"]["tumour_difference_percent"] < 0


def test_out_of_reach_within_the_bound_is_reported_not_forced():
    _, r = run(max_dose_per_session=4.0)
    assert r["equivalent"][0]["tumour"]["dose_per_session"] is None


def test_organ_difference_matches_its_definition():
    s, r = run()
    row = r["equivalent"][-1]
    for organ in ORGANS:
        under = eqd2(s, organ, row["tumour"]["dose_per_session"], row["sessions"])[1]
        assert row["organs"][organ]["eqd2_with_tumour_schedule"] == under
        assert row["organs"][organ]["difference_with_tumour_schedule_percent"] == round(
            100 * (under / r["planned"]["organs_eqd2"][organ] - 1), 1)


def test_result_states_its_options_criterion_and_scope():
    _, r = run()
    assert "reproduce_2014=False" in r["options"] and "staircase" in r["options"]
    assert r["resolution_gy"] == 0.01 and "practitioner decides" in r["scope"]
    assert r["with_all_remaining_sessions"]["sessions"] == 5


# ------------------------------------------------------------ the selector itself (unit counter-examples)


def test_selector_never_exceeds_its_bound():
    assert _iso_dose(lambda d: d, 4.005, 4.005) == (None, None)  # 4.01 would be above the bound
    dose, value = _iso_dose(lambda d: d, 4.0, 4.005)
    assert dose == 4.0 and value == 4.0


def test_selector_does_not_read_an_invalid_bound_as_out_of_reach():
    dose, value = _iso_dose(lambda d: d if d <= 5 else None, 3.0, 10.0)
    assert dose == 3.0 and value == 3.0


def test_selector_reports_unreachable_targets():
    assert _iso_dose(lambda d: d, 20.0, 10.0) == (None, None)


def test_selector_settles_on_the_first_step_of_a_staircase():
    step = lambda d: math.floor(d * 2) / 2  # noqa: E731 - effect constant on 0.5 Gy steps
    dose, value = _iso_dose(step, 2.5, 10.0)
    assert dose == 2.5 and value == 2.5


# ------------------------------------------------------------ refused inputs


@pytest.mark.parametrize("changes", [dict(done_sessions=10), dict(done_sessions=-1), dict(max_remaining=0),
                                     dict(gap_days=-1), dict(organs=()), dict(planned_dose=0),
                                     dict(planned_sessions=10.0), dict(planned_dose=math.inf),
                                     dict(reference_dose=math.inf), dict(max_dose_per_session=math.inf),
                                     dict(gap_days=math.nan), dict(gap_days=math.inf), dict(planned_dose=31.0),
                                     dict(max_remaining=61), dict(planned_sessions=True)])
def test_invalid_situations_are_refused(changes):
    with pytest.raises(ValueError):
        check(Situation(**{**BASE, **changes}))


def test_unknown_organ_is_refused():
    with pytest.raises(Exception):
        run(organs=("Not an organ",))
