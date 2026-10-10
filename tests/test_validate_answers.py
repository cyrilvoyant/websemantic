"""Mapping of returned scenarios before the SHACL checks: objects, lists, dotted and indexed paths are flattened;
nothing is completed, a really absent group member stays absent."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation" / "e1"))

import validate_answers as v  # noqa: E402

PYR = [{"field": "V", "value": 1.0}, {"field": "T0", "value": 283.0}, {"field": "P0", "value": 85000.0},
       {"field": "S0", "value": -0.02}]


def answer(values):
    return {"parsed": {"decision": "execute", "values": values}}


@pytest.fixture(scope="module")
def rules():
    return v.shapes()


@pytest.fixture(scope="module")
def cmap():
    return {"pyrcel": v.concepts("pyrcel"), "lqlequiv": v.concepts("lqlequiv")}


def status(values, domain, rules, cmap):
    return v.classify(answer(values), cmap[domain], *rules)[0]


def test_distribution_object_is_read(rules, cmap):
    values = PYR + [{"field": "distribution", "value": {"mu": 0.04, "sigma": 2, "N": 3000}}, {"field": "kappa", "value": 0.6}]
    mapped, unmapped = v.mapped(answer(values), cmap["pyrcel"])
    assert {(c, i) for c, _, i in mapped} >= {("PYR_N", "mode1"), ("PYR_mu", "mode1"), ("PYR_sigma", "mode1"),
                                              ("PYR_kappa", "mode1")}
    assert status(values, "pyrcel", rules, cmap) == "valid"


def test_dotted_distribution_path_is_read(rules, cmap):
    values = PYR + [{"field": "aerosols[0].distribution.N", "value": 1000.0},
                    {"field": "aerosols[0].distribution.mu", "value": 0.05},
                    {"field": "aerosols[0].distribution.sigma", "value": 2.0}, {"field": "aerosols[0].kappa", "value": 0.54}]
    assert status(values, "pyrcel", rules, cmap) == "valid"


def test_list_of_modes_gives_one_instance_per_element(rules, cmap):
    modes = [{"species": "sulfate", "distribution": {"mu": 0.03, "sigma": 1.6, "N": 800.0, "base": "e"}, "kappa": 0.5},
             {"species": "sea salt", "distribution": {"mu": 0.5, "sigma": 2.2, "N": 50.0}, "kappa": 1.2}]
    mapped, unmapped = v.mapped(answer(PYR + [{"field": "aerosols", "value": modes}]), cmap["pyrcel"])
    assert {i for c, _, i in mapped if c == "PYR_N"} == {"mode1", "mode2"}
    assert "base" in unmapped  # unknown member reported, not dropped silently
    assert status(PYR + [{"field": "aerosols", "value": modes}], "pyrcel", rules, cmap) == "valid"


def test_really_absent_member_stays_a_violation(rules, cmap):
    values = PYR + [{"field": "distribution", "value": {"mu": 0.04, "sigma": 2}}, {"field": "kappa", "value": 0.6}]
    assert status(values, "pyrcel", rules, cmap) == "relational violation only"


def test_instances_are_checked_separately(rules, cmap):
    values = PYR + [{"field": "aerosols[0].N", "value": 100}, {"field": "aerosols[0].mu", "value": 0.05},
                    {"field": "aerosols[0].sigma", "value": 2}, {"field": "aerosols[0].kappa", "value": 0.5},
                    {"field": "aerosols[1].N", "value": 50}, {"field": "aerosols[1].kappa", "value": 1.2}]
    mapped, _ = v.mapped(answer(values), cmap["pyrcel"])
    assert {i for c, _, i in mapped if c == "PYR_kappa"} == {"mode1", "mode2"}
    assert status(values, "pyrcel", rules, cmap) == "relational violation only"


def test_non_numeric_index_is_its_own_instance(cmap):
    mapped, _ = v.mapped(answer([{"field": "aerosols[k].mu", "value": 0.1}]), cmap["pyrcel"])
    assert mapped == [("PYR_mu", 0.1, "mode-k")]


def test_list_of_courses(rules, cmap):
    courses = [{"dose_per_fraction": 2.0, "n_fractions": 25, "gap_days": 0},
               {"dose_per_fraction": 2.0, "n_fractions": 5, "gap_days": 10}]
    values = [{"field": "organ", "value": "Rectum"}, {"field": "courses", "value": courses}]
    mapped, _ = v.mapped(answer(values), cmap["lqlequiv"])
    assert {(c, i) for c, x, i in mapped if c == "LQL_n_fractions"} == {("LQL_n_fractions", "course1"),
                                                                         ("LQL_n_fractions", "course2")}
    indexed = [{"field": "organ", "value": "Rectum"}, {"field": "courses[1].n_fractions", "value": 5}]
    assert v.mapped(answer(indexed), cmap["lqlequiv"])[0][-1] == ("LQL_n_fractions", 5, "course2")


def test_plain_fields_unchanged(cmap):
    mapped, unmapped = v.mapped(answer(PYR + [{"field": "N", "value": 1000}, {"field": "bins", "value": 50}]),
                                cmap["pyrcel"])
    assert ("PYR_N", 1000, "mode1") in mapped and ("PYR_V", 1.0, "1") in mapped
    assert unmapped == ["bins"]
