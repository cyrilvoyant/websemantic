"""Output meanings reviewed against the pinned TLS implementation, not LLM guesses."""


def column_metadata(name, table):
    if table == "daily" and name == "energy_kwh":
        return {"quantity": "energy", "unit": "kWh", "meaning": "Somme des énergies des pas natifs de la journée, réalisation 0."}
    if table == "daily" and name == "mean_kw":
        return {"quantity": "power", "unit": "kW", "meaning": "Moyenne des puissances des pas natifs de la journée, réalisation 0."}
    if name.endswith("_kw") or (table == "envelope" and name in ("median", "p10", "p90", "mean")):
        return {"quantity": "power", "unit": "kW", "meaning": "Puissance électrique calculée."}
    definitions = {
        "energy_kwh": ("energy", "kWh", "Énergie du pas : power_kw × freq_minutes / 60."),
        "total_mwh": ("energy", "MWh", "Énergie de toute la période : somme des energy_kwh / 1000."),
        "annualized_mwh": ("annualized_energy", "MWh/an", "Extrapolation : total_mwh × 365 / n_days ; pas une année observée."),
        "specific_kwh_m_year": ("length_normalized_annualized_energy", "kWh/(m·an)", "annualized_mwh × 1000 / length_m ; ensemble des tubes, par mètre de longueur du tunnel, pas par mètre-tube."),
        "load_factor": ("power_ratio", "1", "mean_kw / peak_kw par réalisation ; sans dimension, 0,6 équivaut à 60 %."),
        "timestamp": ("time", "ISO 8601", "Horodatage sans fuseau horaire déclaré ; aucune localisation déduite."),
        "hour_int": ("hour_of_day", "h", "Heure du jour, de 0 à 23 ; pas une durée."),
        "dayofweek": ("weekday_index", "1", "Indice : lundi 0, dimanche 6."),
        "traffic_index": ("relative_traffic_index", "1", "Indice relatif de trafic ; pas un nombre de véhicules par jour."),
        "pollution_event": ("event_flag", "1", "Indicateur binaire d'événement de pollution simulé."),
        "accident_event": ("event_flag", "1", "Indicateur binaire d'accident simulé."),
        "n_pollution_events": ("transition_count", "1", "Nombre de transitions 0 vers 1 dans la série pollution_event ; un événement actif au premier pas n'est pas compté."),
        "n_accident_events": ("transition_count", "1", "Nombre de transitions 0 vers 1 dans la série accident_event ; un événement actif au premier pas n'est pas compté."),
        "run": ("identifier", None, "Identifiant de réalisation Monte Carlo, à partir de 0."),
        "seed": ("identifier", None, "Graine pseudo-aléatoire : base_seed + run."),
        "season": ("category", None, "Saison du calendrier simulé ; ne prouve pas une couverture annuelle."),
        "day_type": ("category", None, "Jour de semaine ou week-end du calendrier simulé."),
    }
    if name not in definitions:
        raise ValueError(f"Sortie TLS non qualifiée : {table}.{name}")
    quantity, unit, meaning = definitions[name]
    return {"quantity": quantity, "unit": unit, "meaning": meaning}


def qualify(outputs, experiment):
    aggregations = {
        "daily": "Agrégation journalière de la réalisation 0 : somme de l'énergie et moyenne de la puissance ; pas une médiane Monte Carlo. Les dates suivent le calendrier sans fuseau déclaré.",
        "representative": "Réalisation 0 au pas natif ; exemple de trajectoire, pas la médiane.",
        "kpis": "Une ligne par réalisation sur toute la période simulée.",
        "envelope": "Puissances moyennées par heure dans chaque réalisation, puis statistiques entre réalisations. p10/p90 sont des quantiles empiriques, pas un intervalle de confiance.",
        "season_profiles": "Puissance moyenne par saison et heure du jour, dans chaque réalisation, uniquement sur les jours simulés.",
    }
    return {
        "schema_version": "tls-output-qualification-1",
        "data_origin": "synthetic_simulation",
        "spatial_scope": "Ensemble du tunnel et de ses tubes ; aucune coordonnée géographique déclarée.",
        "temporal_scope": {
            "start_date": experiment["start_date"],
            "duration_days": experiment["n_days"],
            "native_step_minutes": experiment["freq_minutes"],
            "timezone": None,
        },
        "monte_carlo": {"realizations": experiment["n_runs"], "base_seed": experiment["base_seed"]},
        "fitness_for_use": {
            "admitted": "Exploration des sorties du modèle sous les hypothèses déclarées.",
            "excluded": "Certification, consommation réelle sans calibration, classement fort/faible non paramétré.",
            "evidence_status": "Contrôles logiciels et calculs ; aucune validation terrain.",
        },
        "tables": {
            name: {
                "file": f"{name}.csv",
                "aggregation": aggregations[name],
                "rows": len(table),
                "columns": {column: column_metadata(column, name) for column in table.columns},
            }
            for name, table in outputs.items()
        },
    }
