"""Descriptor-driven RDF vocabulary and evidence/provenance export."""

import json
import re
from hashlib import sha256

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

WS = Namespace("https://w3id.org/websemantic/ns#")
PROV = Namespace("http://www.w3.org/ns/prov#")
def concept(descriptor, name):
    """Keep model concepts distinct when graphs from several simulators are merged."""
    for group in ('inputs', 'experiment', 'outputs'):
        spec = descriptor.get(group, {}).get(name, {})
        if isinstance(spec, dict) and spec.get('ontology_concept'):
            return WS[spec['ontology_concept']]
    software = descriptor.get('software', {})
    identity = software.get('repository') or software.get('name', 'unnamed')
    scope = descriptor.get('semantics', {}).get('namespace') or 'software-' + sha256(identity.encode()).hexdigest()[:16]
    return WS[f'{scope}/{name}']


def definitions(descriptor):
    return {name: (spec.get('label', name), spec.get('display_unit', spec.get('unit') or 'sans unité'),
                   spec.get('definition', 'Définition non renseignée.'))
            for group in ('inputs', 'experiment') for name, spec in descriptor.get(group, {}).items()}


def vocabulary(descriptor, qualification=None):
    graph = Graph()
    graph.bind("ws", WS)
    graph.bind("skos", SKOS)
    graph.bind("prov", PROV)
    for cls in ("Parameter", "Scenario", "SimulationOutput", "Hypothesis", "UserValue", "Intent", "OperationalSetting"):
        graph.add((WS[cls], RDF.type, RDFS.Class))
    scheme = WS['vocabulary/' + sha256(json.dumps(descriptor.get('software', {}), sort_keys=True).encode()).hexdigest()[:16]]
    graph.add((scheme, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme, SKOS.prefLabel, Literal(descriptor.get('software', {}).get('name', 'Scientific software'))))
    for entry in descriptor.get('model_equations', []):
        equation = concept(descriptor, entry['id'])
        graph.add((equation, RDF.type, SKOS.Concept))
        graph.add((equation, SKOS.inScheme, scheme))
        graph.add((equation, SKOS.prefLabel, Literal(entry['label'], lang='fr')))
        graph.add((equation, SKOS.definition, Literal(entry['meaning'], lang='fr')))
        graph.add((equation, WS.expression, Literal(entry['expression'])))
        graph.add((equation, WS.unitSymbol, Literal(entry['unit'])))
        graph.add((equation, WS.implementationReference, Literal(entry['reference'])))
    for group in ('inputs', 'experiment', 'outputs'):
        category = concept(descriptor, 'group/' + group)
        graph.add((category, RDF.type, SKOS.Concept))
        graph.add((category, SKOS.prefLabel, Literal(group)))
        graph.add((category, SKOS.inScheme, scheme))
        graph.add((scheme, SKOS.hasTopConcept, category))
    for cls in ('Parameter', 'Scenario', 'SimulationOutput'):
        graph.add((WS[cls], RDFS.subClassOf, PROV.Entity))
    graph.add((WS.OperationalSetting, RDFS.subClassOf, WS.Parameter))
    graph.add((WS.Hypothesis, RDFS.subClassOf, WS.Parameter))
    graph.add((WS.UserValue, RDFS.subClassOf, WS.Parameter))
    if descriptor.get('comparison', {}).get('enabled'):
        comparison = concept(descriptor, 'comparison')
        graph.add((comparison, RDF.type, SKOS.Concept))
        graph.add((comparison, SKOS.inScheme, scheme))
        graph.add((comparison, SKOS.prefLabel, Literal('Comparaison de deux scénarios', lang='fr')))
        graph.add((comparison, SKOS.definition, Literal(descriptor['comparison']['output_policy'], lang='fr')))
        graph.add((comparison, WS.scenarioCount, Literal(2)))
        graph.add((WS.ComparisonActivity, RDF.type, RDFS.Class))
        graph.add((WS.ComparisonActivity, RDFS.subClassOf, PROV.Activity))
        for path in descriptor['comparison']['controlled_fields']:
            graph.add((comparison, WS.controlledParameter, concept(descriptor, path.split('.')[-1])))
    property_definitions = {
        "request": "Demande ayant produit la configuration.",
        "task": "Tâche déclarée du scénario.",
        "revision": "Révision du logiciel effectivement exécuté.",
        "repository": "Dépôt source du logiciel.",
        "modelComponent": "Composante du modèle à laquelle appartient le paramètre.",
        "implementationReference": "Fonction du backend où le paramètre est utilisé.",
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
        "operationalDefault": "Réglage technique préautorisé par la politique utilisateur, sans hypothèse physique nouvelle.",
        "defaultAuthorization": "Source de l’autorisation du défaut technique fixe.",
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
    for name, domain, range_ in (
        ('hasParameter', WS.Scenario, WS.Parameter),
        ('value', WS.Parameter, RDFS.Literal),
        ('accepted', WS.Parameter, RDFS.Literal),
        ('concept', RDFS.Resource, SKOS.Concept),
    ):
        graph.add((WS[name], RDFS.domain, domain))
        graph.add((WS[name], RDFS.range, range_))
    specs = {name: (group, spec) for group in ("inputs", "experiment")
             for name, spec in descriptor.get(group, {}).items()}
    for name, (label, unit, definition) in definitions(descriptor).items():
        term = concept(descriptor, name)
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.prefLabel, Literal(label, lang="fr")))
        graph.add((term, SKOS.definition, Literal(definition, lang="fr")))
        graph.add((term, WS.unitSymbol, Literal(unit)))
        group, spec = specs[name]
        graph.add((term, SKOS.inScheme, scheme))
        graph.add((term, SKOS.broader, concept(descriptor, 'group/' + group)))
        graph.add((term, SKOS.notation, Literal(f'{group}.{name}')))
        for key, predicate in (('quantity_kind', WS.quantity), ('model_component', WS.modelComponent), ('reference_implementation', WS.implementationReference)):
            if spec.get(key):
                graph.add((term, predicate, Literal(spec[key])))
        if spec.get('scope_note'):
            graph.add((term, SKOS.scopeNote, Literal(spec['scope_note'], lang='fr')))
        if spec.get('qualitative_scale'):
            graph.add((term, WS.qualitativeScale, Literal(json.dumps(spec['qualitative_scale'], ensure_ascii=False, sort_keys=True), datatype=RDF.JSON)))
        if spec.get('qualitative_policy'):
            graph.add((term, SKOS.scopeNote, Literal(spec['qualitative_policy'], lang='fr')))
        for alias in spec.get("aliases", []):
            graph.add((term, SKOS.altLabel, Literal(alias, lang="fr")))
        graph.add((term, WS.fieldPath, Literal(f"{group}.{name}")))
        graph.add((term, WS.dataType, Literal(spec["type"])))
        if spec.get("unit"):
            graph.add((term, WS.canonicalUnitToken, Literal(spec["unit"])))
        if spec.get("operational_default"):
            graph.add((term, WS.operationalDefault, Literal(True)))
            graph.add((term, WS.defaultAuthorization, Literal(spec["operational_default_source"])))
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
        graph.add((concept(descriptor, intent), RDF.type, WS.Intent))
        graph.add((concept(descriptor, intent), SKOS.related, concept(descriptor, indicator)))
        graph.add((concept(descriptor, intent), WS.requiresIndicator, concept(descriptor, indicator)))
    for name, spec in descriptor.get("outputs", {}).items():
        if not isinstance(spec, dict):
            continue
        term = concept(descriptor, name)
        if spec.get("native_concept"):
            graph.add((term, PROV.wasDerivedFrom, WS[spec["native_concept"]]))
            graph.add((term, WS.conversionFactor, Literal(spec["conversion_factor"])))
        if spec.get("unit"):
            graph.add((term, WS.canonicalUnitToken, Literal(spec["unit"])))
            if spec["unit"].startswith("unit:"):
                graph.add((term, WS.canonicalUnit, URIRef("http://qudt.org/vocab/unit/" + spec["unit"][5:])))
    if qualification:
        for table, info in qualification["tables"].items():
            term = concept(descriptor, f"outputs/{table}")
            graph.add((term, RDF.type, SKOS.Concept))
            graph.add((term, SKOS.inScheme, scheme))
            graph.add((term, SKOS.broader, concept(descriptor, "group/outputs")))
            graph.add((term, SKOS.prefLabel, Literal(table)))
            graph.add((term, WS.aggregation, Literal(info["aggregation"], lang="fr")))
            for column, metadata in info["columns"].items():
                field = concept(descriptor, f"outputs/{table}/{column}")
                graph.add((term, WS.hasColumn, field))
                graph.add((field, RDF.type, SKOS.Concept))
                graph.add((field, SKOS.inScheme, scheme))
                graph.add((field, SKOS.broader, term))
                graph.add((field, WS.concept, concept(descriptor, column)))
                graph.add((concept(descriptor, column), RDF.type, SKOS.Concept))
                graph.add((concept(descriptor, column), SKOS.prefLabel, Literal(column)))
                graph.add((field, SKOS.definition, Literal(metadata["meaning"], lang="fr")))
                if "quantity" in metadata:
                    graph.add((field, WS.quantity, Literal(metadata["quantity"])))
                if metadata["unit"]:
                    graph.add((field, WS.unitSymbol, Literal(metadata["unit"])))
    return graph


def describe(name, descriptor):
    graph = vocabulary(descriptor)
    return tuple(str(graph.value(concept(descriptor, name), predicate)) for predicate in (SKOS.prefLabel, WS.unitSymbol, SKOS.definition))


def export_semantics(scenario, qualification, target, descriptor):
    graph = vocabulary(descriptor, qualification)
    node = WS["scenario/" + target.name]
    graph.add((node, RDF.type, WS.Scenario))
    graph.add((node, WS.request, Literal(scenario.request)))
    graph.add((node, WS.task, Literal(scenario.task)))
    activity = WS['run/' + target.name]
    software = descriptor.get('software', {})
    agent = WS['software/' + sha256(json.dumps(software, sort_keys=True).encode()).hexdigest()[:16]]
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, PROV.used, node))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    graph.add((agent, RDF.type, PROV.SoftwareAgent))
    graph.add((agent, RDFS.label, Literal(software.get('name', 'Scientific software'))))
    if software.get('commit'):
        graph.add((agent, WS.revision, Literal(software['commit'])))
    if software.get('repository'):
        graph.add((agent, WS.repository, URIRef(software['repository'])))
    for group in ("inputs", "experiment"):
        for name, record in getattr(scenario, group).items():
            parameter = WS[f"{target.name}/{group}/{name}"]
            graph.add((node, WS.hasParameter, parameter))
            graph.add((parameter, RDF.type, WS.Parameter))
            if descriptor[group][name].get('operational_default'):
                graph.add((parameter, RDF.type, WS.OperationalSetting))
            if record.origin == 'provided':
                graph.add((parameter, RDF.type, WS.UserValue))
            elif not descriptor[group][name].get('operational_default'):
                graph.add((parameter, RDF.type, WS.Hypothesis))
            definition = concept(descriptor, name)
            graph.add((parameter, WS.concept, definition))
            graph.add((definition, RDF.type, WS.ParameterDefinition))
            spec = descriptor[group][name]
            if spec.get('group_instance'):
                graph.add((parameter, WS.groupInstance, Literal(spec['group_instance'])))
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
        graph.add((output, PROV.wasGeneratedBy, activity))
        graph.add((output, PROV.atLocation, URIRef((target / info.get('file', table + '.csv')).resolve().as_uri())))
        graph.add((output, WS.aggregation, Literal(info["aggregation"], lang="fr")))
        for name, metadata in info["columns"].items():
            column = WS[f"{target.name}/outputs/{table}/{name}"]
            graph.add((output, WS.hasColumn, column))
            if metadata.get("quantity"):
                graph.add((column, WS.quantity, Literal(metadata["quantity"])))
            graph.add((column, WS.meaning, Literal(metadata["meaning"], lang="fr")))
            if metadata["unit"]:
                graph.add((column, WS.unitSymbol, Literal(metadata["unit"])))
    graph.serialize(target / "semantics.ttl", format="turtle")
