"""Competency questions answered by the common core ontology (graph mechanism only)."""

from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
WS = Namespace("https://w3id.org/websemantic/ns#")
PREFIX = """
PREFIX ws: <https://w3id.org/websemantic/ns#>
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
    assert {row.sw for row in rows} == {WS.TLS, WS.LQLEquiv, WS.Pyrcel}
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


def full_graph():
    g = graph()
    for name in ("lqlequiv.ttl", "pyrcel.ttl"):
        g.parse(ROOT / "ontology" / name, format="turtle")
    return g


def ask_full(query):
    return list(full_graph().query(PREFIX + query))


def test_extensions_add_no_new_classes():
    core = set(graph().subjects(RDF.type, OWL.Class))
    assert set(full_graph().subjects(RDF.type, OWL.Class)) == core


def test_cq11_eqd_depends_on_reference_dose_default_2_gy():
    rows = ask_full("SELECT ?d WHERE { ws:LQL_eqd_oar ws:dependsOnReference ?r . ?r ws:codeDefault ?d }")
    assert [float(r.d) for r in rows] == [2.0]


def test_cq13_total_dose_is_derived_not_independent():
    rows = ask_full("SELECT ?p WHERE { ws:LQL_total_dose ws:derivedFrom ?p }")
    assert {r.p for r in rows} == {WS.LQL_dose_per_fraction, WS.LQL_n_fractions}


def test_cq14_per_course_flags_invalidate_matching_outputs_only():
    rows = ask_full("SELECT ?flag ?out WHERE { ?flag ws:invalidates ?out }")
    pairs = {(r.flag, r.out) for r in rows}
    assert pairs == {(WS.LQL_oar_saturated, WS.LQL_eqd_oar), (WS.LQL_tumour_saturated, WS.LQL_eqd_tumour)}
    g = full_graph()
    for flag, _ in pairs:  # direction: the subject is a backend boolean flag, not the invalidated quantity
        assert "saturated" in str(g.value(flag, WS.apiVariable)) and g.value(flag, WS.canonicalUnit) is None


def test_cq15_and_cq19_vague_terms_trigger_clarification_not_values():
    for field in ("LQL_dose_per_fraction", "PYR_N", "PYR_V"):
        policy = ask_full(f"ASK {{ ?c a ws:ClarificationPolicy ; ws:appliesTo ws:{field} }}")
        assert bool(policy[0]), field
    mapped = ask_full('ASK { ?m a ws:QualifierMapping ; skos:altLabel "hypofractionnement modéré"@fr }')
    assert not bool(mapped[0])


def test_cq17_relative_humidity_and_s0_are_one_quantity():
    assert bool(ask_full("ASK { ws:PYR_RH ws:convertibleTo ws:PYR_S0 ; ws:derivationRule ?r }")[0])


def test_cq18_nd_unit_differs_from_input_number_unit():
    rows = ask_full("SELECT ?u ?v WHERE { ws:PYR_Nd ws:canonicalUnit ?u . ws:PYR_N ws:canonicalUnit ?v }")
    assert [(str(r.u).rsplit('/', 1)[1], str(r.v).rsplit('/', 1)[1]) for r in rows] == [("PER-M3", "PER-CentiM3")]


def test_cq12_parcel_task_requires_eight_parameters_with_units():
    rows = ask_full("""SELECT ?p ?u WHERE { ws:TaskParcelActivation ws:requiresParameter ?p .
                       OPTIONAL { ?p ws:canonicalUnit ?u } }""")
    assert len(rows) == 8 and all(r.u is not None for r in rows)


def test_all_canonical_units_are_qudt():
    for _, _, unit in full_graph().triples((None, WS.canonicalUnit, None)):
        assert str(unit).startswith("http://qudt.org/vocab/unit/")


def test_cq21_thoracic_targets_from_group():
    rows = ask_full("""SELECT ?n WHERE { ws:LQL_group_thoracic skos:member ?m . ?m skos:prefLabel ?n ;
                       skos:note ?k FILTER(CONTAINS(?k, "tumour_site")) }""")
    assert sorted(str(r[0]) for r in rows) == ["Breast carcinoma", "Lung", "Oesophagus"]


def test_cq22_group_members_are_library_values_not_a_choice_of_organ():
    import yaml
    d = yaml.safe_load((ROOT / "descriptors" / "lqlequiv" / "descriptor.yaml").read_text(encoding="utf-8"))
    names = set(d["inputs"]["organ"]["values"]) | set(d["inputs"]["tumour_site"]["values"])
    labels = {str(r[0]) for r in ask_full("SELECT ?n WHERE { ?m skos:inScheme ws:LQL_AnatomyScheme ; skos:prefLabel ?n }")}
    assert labels and labels <= names
    assert not ask_full("SELECT ?x WHERE { ws:TaskScheduleComparison ws:codeDefault ?x }")


def test_cq23_better_means_dominance():
    rule = str(ask_full("SELECT ?r WHERE { ws:TaskScheduleComparison ws:derivationRule ?r }")[0][0])
    assert "dominates" in rule and "trade-off" in rule
    assert ask_full("ASK { ws:LQLContract ws:supportsTask ws:TaskScheduleComparison }")[0] is True


def test_cq24_moderate_hypofractionation_is_asked():
    assert ask_full("""ASK { ?p a ws:ClarificationPolicy ; skos:altLabel "hypofractionnement modéré"@fr ;
                         ws:appliesTo ws:LQL_dose_per_fraction }""")[0] is True
