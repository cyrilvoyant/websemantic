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


def vocabulary(descriptor, qualification=None):
    graph = Graph()
    graph.bind("ws", WS)
    graph.bind("skos", SKOS)
    graph.bind("prov", PROV)
    for cls in ("Parameter", "Scenario", "SimulationOutput", "Hypothesis", "UserValue", "Intent"):
        graph.add((WS[cls], RDF.type, RDFS.Class))
    graph.add((WS.Hypothesis, RDFS.subClassOf, WS.Parameter))
    graph.add((WS.UserValue, RDFS.subClassOf, WS.Parameter))
    property_definitions = {
        "hasParameter": "Relie un scénario à ses enregistrements de paramètres.",
        "concept": "Relie un enregistrement à la définition du paramètre.",
        "value": "Valeur typée dans l'unité canonique déclarée.",
        "unitSymbol": "Symbole lisible ; ne constitue pas un alignement QUDT vérifié.",
        "canonicalUnitToken": "Identifiant d'unité utilisé par le contrôle Python.",
        "accepted": "Acceptation explicite de l'hypothèse.",
        "origin": "Origine : provided, default, assumption ou missing.",
        "evidence": "Extrait exact de la demande ; présence ne prouve pas la justesse sémantique.",
        "dataType": "Type attendu par le contrôle déterministe.",
        "fieldPath": "Chemin exact inputs.nom ou experiment.nom.",
        "defaultValue": "Proposition du profil ; jamais acceptée automatiquement par le graphe.",
        "allowedValue": "Valeur catégorielle autorisée.",
        "unitAlias": "Unité reconnue à l'interprétation ; conversion avant validation.",
        "minimum": "Borne minimale incluse.",
        "maximum": "Borne maximale incluse.",
        "minimumExclusive": "Borne minimale exclue.",
        "maximumExclusive": "Borne maximale exclue.",
        "boundAuthority": "Origine déclarée de la borne ; code ou politique du prototype.",
        "requiresIndicator": "Indicateur associé à l'intention.",
        "aggregation": "Méthode de regroupement de la table calculée.",
        "hasColumn": "Colonne d'une table calculée.",
        "meaning": "Sens scientifique et limites de la quantité.",
        "quantity": "Nature de la quantité : énergie, puissance, indice, identifiant, etc.",
    }
    for name, meaning in property_definitions.items():
        graph.add((WS[name], RDF.type, RDF.Property))
        graph.add((WS[name], RDFS.comment, Literal(meaning, lang="fr")))
    specs = {name: (group, spec) for group in ("inputs", "experiment")
             for name, spec in descriptor.get(group, {}).items()}
    for name, (label, unit, definition) in definitions(descriptor).items():
        term = WS[name]
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.prefLabel, Literal(label, lang="fr")))
        graph.add((term, SKOS.definition, Literal(definition, lang="fr")))
        graph.add((term, WS.unitSymbol, Literal(unit)))
        group, spec = specs[name]
        graph.add((term, WS.fieldPath, Literal(f"{group}.{name}")))
        graph.add((term, WS.dataType, Literal(spec["type"])))
        if spec.get("unit"):
            graph.add((term, WS.canonicalUnitToken, Literal(spec["unit"])))
        if "default" in spec:
            graph.add((term, WS.defaultValue, Literal(spec["default"])))
        for value in spec.get("choices", spec.get("values", [])):
            graph.add((term, WS.allowedValue, Literal(value)))
        for alias in spec.get("unit_aliases", []):
            if alias is not None:
                graph.add((term, WS.unitAlias, Literal(alias)))
        bounds = spec.get("bounds", {})
        for key, predicate in (("min", "minimum"), ("max", "maximum"),
                               ("min_exclusive", "minimumExclusive"), ("max_exclusive", "maximumExclusive"),
                               ("authority", "boundAuthority")):
            if key in bounds:
                graph.add((term, WS[predicate], Literal(bounds[key])))
    for intent, indicator in descriptor.get("semantics", {}).get("intent_indicators", {}).items():
        graph.add((WS[intent], RDF.type, WS.Intent))
        graph.add((WS[intent], WS.requiresIndicator, WS[indicator]))
    if qualification:
        for table, info in qualification["tables"].items():
            term = WS[f"outputs/{table}"]
            graph.add((term, RDF.type, SKOS.Concept))
            graph.add((term, SKOS.prefLabel, Literal(table)))
            graph.add((term, WS.aggregation, Literal(info["aggregation"], lang="fr")))
            for column, metadata in info["columns"].items():
                field = WS[f"outputs/{table}/{column}"]
                graph.add((term, WS.hasColumn, field))
                graph.add((field, RDF.type, SKOS.Concept))
                graph.add((field, WS.concept, WS[column]))
                graph.add((WS[column], RDF.type, SKOS.Concept))
                graph.add((WS[column], SKOS.prefLabel, Literal(column)))
                graph.add((field, SKOS.definition, Literal(metadata["meaning"], lang="fr")))
                if "quantity" in metadata:
                    graph.add((field, WS.quantity, Literal(metadata["quantity"])))
                if metadata["unit"]:
                    graph.add((field, WS.unitSymbol, Literal(metadata["unit"])))
    return graph


def describe(name, descriptor):
    graph = vocabulary(descriptor)
    return tuple(str(graph.value(WS[name], predicate)) for predicate in (SKOS.prefLabel, WS.unitSymbol, SKOS.definition))


def export_semantics(scenario, qualification, target, descriptor):
    graph = Graph()
    for triple in vocabulary(descriptor, qualification):
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
