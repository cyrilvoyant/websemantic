"""Alignment module (ontology/alignments.ttl): only declared core terms, no equivalence, and simulated outputs read as
SOSA results under RDFS inference."""

from pathlib import Path

import pytest
from rdflib import BNode, Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
WSEM = Namespace("https://w3id.org/websemantic/ns#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
PROV = Namespace("http://www.w3.org/ns/prov#")


def graphs():
    core = Graph().parse(ROOT / "ontology" / "core.ttl", format="turtle")
    alignments = Graph().parse(ROOT / "ontology" / "alignments.ttl", format="turtle")
    return core, alignments


def test_alignments_use_only_core_terms_and_no_equivalence():
    core, alignments = graphs()
    declared = set(core.subjects(RDF.type, OWL.Class)) | set(core.subjects(RDF.type, OWL.ObjectProperty))
    aligned = {s for s, p, _ in alignments if p in (RDFS.subClassOf, RDFS.subPropertyOf) and str(s).startswith(str(WSEM))}
    assert aligned and aligned <= declared
    assert not list(alignments.triples((None, OWL.equivalentClass, None)))


def test_a_simulation_output_is_a_sosa_result_under_rdfs_inference():
    owlrl = pytest.importorskip("owlrl")
    core, alignments = graphs()
    data = core + alignments
    output = BNode()
    data.add((output, RDF.type, WSEM.SimulationOutput))
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(data)
    assert (output, RDF.type, SOSA.Result) in data and (output, RDF.type, PROV.Entity) in data


def test_a_run_graph_reads_as_an_observation_by_the_pinned_code(tmp_path):
    owlrl = pytest.importorskip("owlrl")
    from websemantic.core.validation import Scenario
    from websemantic.registry import load_descriptor
    from websemantic.semantics import export_semantics

    descriptor = load_descriptor(ROOT, "lql")
    target = tmp_path / "run"
    target.mkdir()
    qualification = {"tables": {"indicators": {"aggregation": "Fixture only", "columns": {"bed": {"meaning": "Fixture", "unit": "Gy"}}}}}
    export_semantics(Scenario("Fixture request", descriptor["tasks"]["supported"][0]), qualification, target, descriptor)
    core, alignments = graphs()
    data = core + alignments + Graph().parse(target / "semantics.ttl", format="turtle")
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(data)
    rows = list(data.query("""
        PREFIX sosa: <http://www.w3.org/ns/sosa/> PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX schema: <https://schema.org/> PREFIX wsem: <https://w3id.org/websemantic/ns#>
        SELECT ?revision WHERE {
            ?result a sosa:Result ; prov:wasGeneratedBy ?run .
            ?run a sosa:Observation ; prov:wasAssociatedWith ?code .
            ?code a sosa:Sensor , schema:SoftwareSourceCode ; wsem:revision ?revision }"""))
    assert [str(row.revision) for row in rows] == [descriptor["software"]["commit"]]
