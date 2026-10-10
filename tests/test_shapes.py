"""SHACL shapes read bounds and relations from the ontology (condition B3 mechanisms)."""

from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import RDF

pyshacl = pytest.importorskip("pyshacl")

ROOT = Path(__file__).resolve().parents[1]
WS = Namespace("https://w3id.org/websemantic/ns#")


def ontology():
    g = Graph()
    for name in ("core.ttl", "lqlequiv.ttl", "pyrcel.ttl"):
        g.parse(ROOT / "ontology" / name, format="turtle")
    return g


def scenario(values):
    """values: dict concept -> value (single instance "1") or list of (concept, value, instance)."""
    items = values if isinstance(values, list) else [(c, v, "1") for c, v in values.items()]
    g = Graph()
    s = WS.TestScenario
    g.add((s, RDF.type, WS.Scenario))
    for concept, value, instance in items:
        r = BNode()
        g.add((r, RDF.type, WS.Parameter))
        g.add((r, WS.concept, WS[concept]))
        g.add((r, WS.value, Literal(value)))
        g.add((r, WS.groupInstance, Literal(instance)))
        g.add((s, WS.hasParameter, r))
    return g


def messages(values):
    shapes = Graph().parse(ROOT / "ontology" / "shapes.ttl", format="turtle")
    data = scenario(values) + ontology()  # bounds and relations are read from the merged graph
    conforms, report, _ = pyshacl.validate(data, shacl_graph=shapes, advanced=True, inference="none")
    assert not isinstance(report, str) and hasattr(report, 'objects'), report
    texts = [str(o) for o in report.objects(None, Namespace("http://www.w3.org/ns/shacl#").resultMessage)]
    return conforms, texts


LQL_OK = {"LQL_dose_per_fraction": 3.0, "LQL_n_fractions": 20, "LQL_reference_dose": 2.0}
PYR_OK = {"PYR_V": 1.0, "PYR_T0": 283.0, "PYR_P0": 85000.0, "PYR_S0": -0.02,
          "PYR_N": 1000.0, "PYR_mu": 0.05, "PYR_sigma": 2.0, "PYR_kappa": 0.54}


def test_reference_scenarios_conform():
    assert messages(LQL_OK)[0]
    assert messages(PYR_OK)[0]
    assert messages({**LQL_OK, "LQL_total_dose": 60.0})[0]
    assert messages({**PYR_OK, "PYR_RH": 0.98})[0]


def test_bound_from_graph_rejects_negative_dose_and_zero_reference():
    conforms, texts = messages({**LQL_OK, "LQL_dose_per_fraction": -1.0, "LQL_reference_dose": 0.0})
    assert not conforms and len([m for m in texts if "bound" in m]) == 2


def test_derived_total_dose_conflict_is_detected():  # LQL-P09: 20 x 3 Gy announced as 66 Gy
    conforms, texts = messages({**LQL_OK, "LQL_total_dose": 66.0})
    assert not conforms and any("total dose" in t for t in texts)


def test_relative_humidity_and_s0_conflict_is_detected():  # PYR-P09: RH 95 % with S0 = -0.02
    conforms, texts = messages({**PYR_OK, "PYR_RH": 0.95})
    assert not conforms and any("one state" in t for t in texts)


def test_incomplete_aerosol_mode_is_detected():
    partial = {k: v for k, v in PYR_OK.items() if k != "PYR_kappa"}
    conforms, texts = messages(partial)
    assert not conforms and any("Incomplete parameter group" in t for t in texts)


def test_s0_bounds_from_profile_policy():
    conforms, _ = messages({**PYR_OK, "PYR_S0": 0.01})
    assert not conforms


MODE = ("PYR_N", "PYR_mu", "PYR_sigma", "PYR_kappa")
BASE = [("PYR_V", 1.0, "1"), ("PYR_T0", 283.0, "1"), ("PYR_P0", 85000.0, "1"), ("PYR_S0", -0.02, "1")]


def test_two_complete_aerosol_modes_conform():
    modes = [(c, v, k) for k in ("m1", "m2") for c, v in zip(MODE, (1000.0, 0.05, 2.0, 0.54))]
    assert messages(BASE + modes)[0]


def test_incomplete_second_mode_is_not_masked_by_first():
    modes = [(c, v, "m1") for c, v in zip(MODE, (1000.0, 0.05, 2.0, 0.54))] + [("PYR_N", 50.0, "m2"), ("PYR_mu", 0.5, "m2")]
    conforms, texts = messages(BASE + modes)
    assert not conforms and any("instance m2" in m for m in texts) and not any("instance m1" in m for m in texts)


def course(k, d, n, total):
    return [("LQL_dose_per_fraction", d, k), ("LQL_n_fractions", n, k), ("LQL_total_dose", total, k)]


def test_consistent_courses_are_not_cross_mixed():
    assert messages(course("c1", 2.0, 25, 50.0) + course("c2", 3.0, 5, 15.0))[0]


def test_inconsistent_second_course_is_detected():
    conforms, texts = messages(course("c1", 2.0, 25, 50.0) + course("c2", 3.0, 5, 20.0))
    assert not conforms and sum("total dose" in m for m in texts) == 1


def test_non_numeric_value_is_rejected():
    conforms, texts = messages({**LQL_OK, "LQL_n_fractions": "trois"})
    assert not conforms and any("Numeric value expected" in m for m in texts)


def test_missing_group_instance_is_rejected_for_repeated_parameters():
    g = scenario(course("c1", 3.0, 20, 66.0))
    for record in list(g.subjects(WS.concept, WS.LQL_total_dose)):
        g.remove((record, WS.groupInstance, None))
    shapes = Graph().parse(ROOT / "ontology" / "shapes.ttl", format="turtle")
    conforms, report, _ = pyshacl.validate(g + ontology(), shacl_graph=shapes, advanced=True, inference="none")
    texts = [str(o) for o in report.objects(None, Namespace("http://www.w3.org/ns/shacl#").resultMessage)]
    assert not conforms and any("lacks wsem:groupInstance" in m for m in texts)


def test_unknown_concept_and_duplicate_value_are_rejected():
    g = scenario({"LQL_reference_dose": 2.0})
    record = next(g.subjects(WS.concept, WS.LQL_reference_dose))
    g.add((record, WS.value, Literal(3.0)))
    g.add((record, WS.concept, WS.NotDeclared))
    shapes = Graph().parse(ROOT / "ontology" / "shapes.ttl", format="turtle")
    conforms, report, _ = pyshacl.validate(g + ontology(), shacl_graph=shapes, advanced=True, inference="none")
    texts = [str(o) for o in report.objects(None, Namespace("http://www.w3.org/ns/shacl#").resultMessage)]
    assert not conforms and any("at most one value" in m for m in texts) and any("known parameter" in m for m in texts)
