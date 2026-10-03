"""Small explicit RDF vocabulary for TLS concepts, units and evidence status."""

import re
from functools import lru_cache
from hashlib import sha256

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

WS = Namespace("https://github.com/cyrilvoyant/websemantic/ns#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DEFINITIONS = {
    "length_m": ("Longueur", "m", "Longueur du tunnel, commune aux tubes."),
    "n_tubes": ("Tubes", "nombre", "Nombre de tubes du tunnel."),
    "n_lanes_per_tube": ("Voies par tube", "nombre", "Nombre de voies dans chaque tube."),
    "altitude_m": ("Altitude", "m", "Altitude du tunnel ; une ville ne fixe pas celle du site."),
    "max_depth_m": ("Couverture maximale", "m", "Épaisseur maximale au-dessus du tunnel dans TLS."),
    "gradient_percent": ("Pente", "%", "Pente longitudinale : 2 % correspond à 2 m par 100 m."),
    "tunnel_context": ("Contexte", "catégorie", "Urbain, périurbain ou rural : modifie le modèle de trafic."),
    "lighting_type": ("Éclairage", "catégorie", "Technologie et commande, pas une intensité lumineuse en lux."),
    "ventilation_type": ("Ventilation", "catégorie", "Type de ventilation modélisé."),
    "aux_kw_per_km_tube": ("Auxiliaires", "kW/(km·tube)", "Puissance auxiliaire par kilomètre et par tube."),
    "base_fixed_kw": ("Charge fixe", "kW", "Puissance constante ajoutée pour l'ensemble du tunnel."),
    "traffic_level": ("Trafic relatif", "1", "Multiplicateur du trafic ; 1 est la référence, pas des véhicules/jour."),
    "morning_peak_hour": ("Pointe du matin", "h du jour", "Heure centrale du pic de trafic, entre 0 et 24."),
    "evening_peak_hour": ("Pointe du soir", "h du jour", "Heure centrale du pic de trafic, entre 0 et 24."),
    "peak_width_h": ("Largeur des pics", "h", "Durée caractéristique des pics de trafic."),
    "traffic_sensitivity": ("Sensibilité au trafic", "1", "Coefficient du modèle, sans dimension."),
    "noise_sigma": ("Bruit multiplicatif", "1", "Écart-type relatif du bruit ; 0,06 correspond à 6 %."),
    "pollution_probability_per_day": ("Probabilité de pollution", "1", "Probabilité par jour ; 0,05 = 5 %, pas un taux mesuré."),
    "accident_probability_per_day": ("Probabilité d'accident", "1", "Probabilité par jour ; 0,015 = 1,5 %."),
    "pollution_sensitivity": ("Sensibilité pollution", "1", "Coefficient de surcroît lié aux événements de pollution."),
    "accident_sensitivity": ("Sensibilité accidents", "1", "Coefficient de surcroît lié aux accidents simulés."),
    "start_date": ("Début", "date", "Premier jour simulé, au format AAAA-MM-JJ."),
    "n_days": ("Durée", "jours", "Nombre de jours effectivement simulés."),
    "freq_minutes": ("Pas de calcul", "min", "Durée entre deux points de calcul."),
    "n_runs": ("Réalisations", "nombre", "Nombre de trajectoires Monte Carlo."),
    "base_seed": ("Graine", "identifiant", "Graine pseudo-aléatoire pour reproduire le calcul."),
}


@lru_cache
def vocabulary():
    graph = Graph()
    graph.bind("ws", WS)
    graph.bind("skos", SKOS)
    graph.bind("prov", PROV)
    for cls in ("Parameter", "Scenario", "SimulationOutput", "Hypothesis", "UserValue", "EnergyIntent"):
        graph.add((WS[cls], RDF.type, RDFS.Class))
    for name, (label, unit, definition) in DEFINITIONS.items():
        term = WS[name]
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.prefLabel, Literal(label, lang="fr")))
        graph.add((term, SKOS.definition, Literal(definition, lang="fr")))
        graph.add((term, WS.unitSymbol, Literal(unit)))
    for intent, indicator in (("energy_demand", "total_mwh"), ("annual_energy", "annualized_mwh"), ("length_efficiency", "specific_kwh_m_year"), ("peak_demand", "peak_kw")):
        graph.add((WS[intent], RDF.type, WS.EnergyIntent))
        graph.add((WS[intent], WS.requiresIndicator, WS[indicator]))
    return graph


def describe(name):
    graph = vocabulary()
    return tuple(str(graph.value(WS[name], predicate)) for predicate in (SKOS.prefLabel, WS.unitSymbol, SKOS.definition))


def export_semantics(scenario, qualification, target):
    graph = Graph()
    for triple in vocabulary():
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
            graph.add((parameter, WS.unitSymbol, Literal(describe(name)[1])))
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
