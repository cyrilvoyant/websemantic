"""Competency questions answered by the common core ontology (graph mechanism only)."""

from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
WS = Namespace("https://github.com/cyrilvoyant/websemantic/ns#")
PREFIX = """
PREFIX ws: <https://github.com/cyrilvoyant/websemantic/ns#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def graph():
    g = Graph()
    g.parse(ROOT / "ontology" / "core.ttl", format="turtle")
    return g


def ask(query):
    return list(graph().query(PREFIX + query))


def test_core_parses_and_declares_ontology():
    g = graph()
    assert (None, RDF.type, OWL.Ontology) in g
    assert len(set(g.subjects(RDF.type, OWL.Class))) >= 25


def test_no_strong_equivalence_to_external_vocabularies():
    assert not list(graph().triples((None, OWL.equivalentClass, None)))


def test_cq1_supported_and_excluded_tasks_per_software():
    rows = ask("""
        SELECT ?sw (COUNT(DISTINCT ?s) AS ?ns) (COUNT(DISTINCT ?e) AS ?ne) WHERE {
          ?sw a ws:Software ; ws:hasContract ?c .
          ?c ws:supportsTask ?s ; ws:excludesTask ?e .
        } GROUP BY ?sw""")
    assert {row.sw for row in rows} == {WS.TLS, WS.LQLEquiv, WS.PVLib}
    assert all(int(row.ns) >= 1 and int(row.ne) >= 1 for row in rows)
    patient = ask("ASK { ws:LQLContract ws:excludesTask ws:TaskPatientDecision }")
    assert bool(patient[0])


def test_cq2_every_qualifier_mapping_requires_acceptance():
    g = graph()
    mappings = set(g.subjects(RDF.type, WS.QualifierMapping))
    assert mappings
    for mapping in mappings:
        assert g.value(mapping, WS.requiresAcceptance) == Literal(True)


def test_cq3_beaucoup_traffic_proposes_1_5():
    rows = ask("""
        SELECT ?v WHERE {
          ?term skos:altLabel "beaucoup"@fr .
          ?m ws:term ?term ; ws:appliesTo ?p ; ws:proposedValue ?v .
          ?p ws:fieldPath "inputs.traffic_level" .
        }""")
    assert [float(row.v) for row in rows] == [1.5]


def test_cq4_lighting_intensity_has_no_mapping_but_a_clarification_policy():
    mapped = ask("ASK { ?m a ws:QualifierMapping ; ws:appliesTo ws:TLS_lighting_type }")
    policy = ask("ASK { ?p a ws:ClarificationPolicy ; ws:appliesTo ws:TLS_lighting_type }")
    assert not bool(mapped[0]) and bool(policy[0])


def test_cq5_additivity_of_outputs():
    g = graph()
    assert g.value(WS.TLS_energy_step, WS.additive) == Literal(True)
    assert g.value(WS.TLS_power, WS.additive) == Literal(False)


def test_cq6_annualised_energy_is_an_extrapolation():
    rows = ask("ASK { ws:TLS_specific_energy ws:aggregation ws:AggExtrapolation }")
    assert bool(rows[0])


def test_value_origin_classes_are_disjoint():
    g = graph()
    groups = [set(g.items(g.value(node, OWL.members))) for node in g.subjects(RDF.type, OWL.AllDisjointClasses)]
    assert {WS.UserValue, WS.Hypothesis, WS.OperationalSetting, WS.UnknownValue} in groups
