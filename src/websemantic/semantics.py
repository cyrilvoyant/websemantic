"""Descriptor-driven RDF vocabulary and evidence/provenance export."""

import re
from hashlib import sha256

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

WS = Namespace("https://github.com/cyrilvoyant/websemantic/ns#")
PROV = Namespace("http://www.w3.org/ns/prov#")
def definitions(descriptor):
    return {name: (spec.get('label', name), spec.get('display_unit', spec.get('unit') or 'sans unité'),
                   spec.get('definition', 'Définition non renseignée.'))
            for group in ('inputs', 'experiment') for name, spec in descriptor.get(group, {}).items()}


def vocabulary(descriptor):
    graph = Graph()
    graph.bind("ws", WS)
    graph.bind("skos", SKOS)
    graph.bind("prov", PROV)
    for cls in ("Parameter", "Scenario", "SimulationOutput", "Hypothesis", "UserValue", "Intent"):
        graph.add((WS[cls], RDF.type, RDFS.Class))
    for name, (label, unit, definition) in definitions(descriptor).items():
        term = WS[name]
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.prefLabel, Literal(label, lang="fr")))
        graph.add((term, SKOS.definition, Literal(definition, lang="fr")))
        graph.add((term, WS.unitSymbol, Literal(unit)))
    for intent, indicator in descriptor.get("semantics", {}).get("intent_indicators", {}).items():
        graph.add((WS[intent], RDF.type, WS.Intent))
        graph.add((WS[intent], WS.requiresIndicator, WS[indicator]))
    return graph


def describe(name, descriptor):
    graph = vocabulary(descriptor)
    return tuple(str(graph.value(WS[name], predicate)) for predicate in (SKOS.prefLabel, WS.unitSymbol, SKOS.definition))


def export_semantics(scenario, qualification, target, descriptor):
    graph = Graph()
    for triple in vocabulary(descriptor):
        graph.add(triple)
    node = WS["scenario/" + target.name]
    graph.add((node, RDF.type, WS.Scenario))
    for group in ("inputs", "experiment"):
        for name, record in getattr(scenario, group).items():
            parameter = WS[f"{target.name}/{group}/{name}"]
            graph.add((node, WS.hasParameter, parameter))
            graph.add((parameter, RDF.type, WS.Parameter))
            graph.add((parameter, RDF.type, WS.UserValue if record.origin == 'provided' else WS.Hypothesis))
            graph.add((parameter, WS.concept, WS[name]))
            graph.add((parameter, WS.value, Literal(record.value)))
            graph.add((parameter, WS.unitSymbol, Literal(describe(name, descriptor)[1])))
            graph.add((parameter, WS.accepted, Literal(record.accepted)))
            graph.add((parameter, WS.origin, Literal(record.origin)))
            if record.source:
                source = WS['source/' + sha256(record.source.encode()).hexdigest()[:16]]
                graph.add((parameter, PROV.wasDerivedFrom, source))
                graph.add((source, RDF.type, PROV.Entity))
                graph.add((source, RDFS.label, Literal(record.source)))
                for url in re.findall(r'https?://[^\s;]+', record.source):
                    graph.add((source, PROV.atLocation, URIRef(url.rstrip('.'))))
            if record.evidence:
                graph.add((parameter, WS.evidence, Literal(record.evidence)))
    for table, info in qualification["tables"].items():
        output = WS[f"{target.name}/outputs/{table}"]
        graph.add((output, RDF.type, WS.SimulationOutput))
        graph.add((output, PROV.wasDerivedFrom, node))
        graph.add((output, WS.aggregation, Literal(info["aggregation"], lang="fr")))
        for name, metadata in info["columns"].items():
            column = WS[f"{target.name}/outputs/{table}/{name}"]
            graph.add((output, WS.hasColumn, column))
            graph.add((column, WS.meaning, Literal(metadata["meaning"], lang="fr")))
            if metadata["unit"]:
                graph.add((column, WS.unitSymbol, Literal(metadata["unit"])))
    graph.serialize(target / "semantics.ttl", format="turtle")
