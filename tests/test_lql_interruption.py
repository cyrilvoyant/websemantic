"""Biologically equivalent resumption of an interrupted fictitious schedule (unchanged LQL-Equiv library)."""

from pathlib import Path

import pytest
import yaml

from websemantic.lql_interruption import Situation, _Model, check, resume

ROOT = Path(__file__).resolve().parents[1]
DESC = yaml.safe_load((ROOT / "descriptors" / "lqlequiv" / "descriptor.yaml").read_text(encoding="utf-8"))
ORGANS = ("Rectum", "Small bowel", "Bladder")


def run(**changes):
    base = dict(tumour="Prostate", organs=ORGANS, planned_dose=3.0, planned_sessions=10, done_sessions=2,
                gap_days=10, max_remaining=5)
    s = Situation(**{**base, **changes})
    return s, resume(s, ROOT, DESC)


def eqd2(s, organ, dose, n):
    model = _Model(ROOT, DESC, s)
    return model.eqd2(organ, [(s.planned_dose, s.done_sessions, 0.0), (dose, n, s.gap_days)])


def test_tumour_equivalence_is_restored_with_the_smallest_dose():
    s, r = run()
    target = r["planned"]["tumour_eqd2"]
    for row in r["equivalent"]:
        if row["tumour"] is None:
            continue
        assert eqd2(s, "Rectum", row["tumour"], row["sessions"])[0] >= target
        assert eqd2(s, "Rectum", round(row["tumour"] - 0.01, 2), row["sessions"])[0] < target


def test_each_organ_equivalence_is_restored_with_the_smallest_dose():
    s, r = run()
    for organ in ORGANS:
        target = r["planned"]["organs_eqd2"][organ]
        row = r["equivalent"][-1]
        dose = row["organs"][organ]["equivalent_dose"]
        assert eqd2(s, organ, dose, row["sessions"])[1] >= target
        assert eqd2(s, organ, round(dose - 0.01, 2), row["sessions"])[1] < target


def test_no_interruption_gives_back_the_planned_dose():
    _, r = run(gap_days=0, max_remaining=8)
    row = r["equivalent"][-1]
    assert row["sessions"] == 8
    assert row["tumour"] == pytest.approx(3.0, abs=0.02)
    assert all(v["equivalent_dose"] == pytest.approx(3.0, abs=0.02) for v in row["organs"].values())


def test_fewer_sessions_need_a_higher_dose_per_session():
    _, r = run()
    doses = [row["tumour"] for row in r["equivalent"] if row["tumour"] is not None]
    assert doses == sorted(doses, reverse=True) and len(set(doses)) == len(doses)


def test_a_longer_interruption_needs_more_dose_for_the_tumour():
    _, short = run(gap_days=5)
    _, long = run(gap_days=30)
    assert long["equivalent"][-1]["tumour"] > short["equivalent"][-1]["tumour"]


def test_uncompensated_resumption_loses_tumour_effect():
    _, r = run()
    assert r["uncompensated"]["sessions"] == 5
    assert r["uncompensated"]["tumour_deficit_percent"] < 0


def test_out_of_reach_is_reported_not_forced():
    _, r = run(max_dose_per_session=4.0)
    assert r["equivalent"][0]["tumour"] is None  # one session cannot restore the effect below 4 Gy


def test_organ_excess_matches_its_definition():
    s, r = run()
    row = r["equivalent"][-1]
    for organ in ORGANS:
        under = eqd2(s, organ, row["tumour"], row["sessions"])[1]
        expected = round(100 * (under / r["planned"]["organs_eqd2"][organ] - 1), 1)
        assert row["organs"][organ]["excess_with_tumour_schedule_percent"] == expected


def test_ideal_uses_all_remaining_sessions_and_states_its_scope():
    _, r = run()
    assert r["ideal"]["sessions"] == 5 and r["ideal"]["tumour"] == r["equivalent"][-1]["tumour"]
    assert "practitioner decides" in r["scope"]


@pytest.mark.parametrize("changes", [dict(done_sessions=10), dict(done_sessions=-1), dict(max_remaining=0),
                                     dict(gap_days=-1), dict(organs=()), dict(planned_dose=0),
                                     dict(planned_sessions=10.0)])
def test_invalid_situations_are_refused(changes):
    base = dict(tumour="Prostate", organs=ORGANS, planned_dose=3.0, planned_sessions=10, done_sessions=2,
                gap_days=10, max_remaining=5)
    with pytest.raises(ValueError):
        check(Situation(**{**base, **changes}))


def test_unknown_organ_is_refused():
    with pytest.raises(Exception):
        run(organs=("Not an organ",))
