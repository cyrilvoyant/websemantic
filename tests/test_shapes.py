"""SHACL shapes read bounds and relations from the ontology (condition B3 mechanisms)."""

from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import RDF

pyshacl = pytest.importorskip("pyshacl")

ROOT = Path(__file__).resolve().parents[1]
WS = Namespace("https://github.com/cyrilvoyant/websemantic/ns#")


def ontology():
    g = Graph()
    for name in ("core.ttl", "lqlequiv.ttl", "pyrcel.ttl"):
        g.parse(ROOT / "ontology" / name, format="turtle")
    return g


def scenario(values):
    g = Graph()
    s = WS.TestScenario
    g.add((s, RDF.type, WS.Scenario))
    for concept, value in values.items():
        r = BNode()
        g.add((r, RDF.type, WS.Parameter))
        g.add((r, WS.concept, WS[concept]))
        g.add((r, WS.value, Literal(value)))
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
    assert not conforms and len([t for t in texts if "bound" in t]) == 2


def test_derived_total_dose_conflict_is_detected():  # LQL-P09: 20 x 3 Gy announced as 66 Gy
    conforms, texts = messages({**LQL_OK, "LQL_total_dose": 66.0})
    assert not conforms and any("total dose" in t for t in texts)


def test_relative_humidity_and_s0_conflict_is_detected():  # PYR-P09: RH 95 % with S0 = -0.02
    conforms, texts = messages({**PYR_OK, "PYR_RH": 0.95})
    assert not conforms and any("one quantity" in t for t in texts)


def test_incomplete_aerosol_mode_is_detected():
    partial = {k: v for k, v in PYR_OK.items() if k != "PYR_kappa"}
    conforms, texts = messages(partial)
    assert not conforms and any("Incomplete parameter group" in t for t in texts)


def test_s0_bounds_from_profile_policy():
    conforms, _ = messages({**PYR_OK, "PYR_S0": 0.01})
    assert not conforms
