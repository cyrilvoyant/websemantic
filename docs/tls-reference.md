# Paramètres et sorties TLS

Document généré par tools/export_tls_contract.py. Le descripteur et les contrôles Python font autorité.

Les défauts scientifiques sont des propositions non calibrées, à accepter explicitement. Tous les paramètres sont requis dans la configuration ; les réglages operational_default sont fournis automatiquement selon la politique utilisateur.

## inputs

| Champ | Définition | Type | Unité canonique / lisible | Défaut proposé | Contraintes déclarées |
|---|---|---|---|---|---|
| `length_m` | Longueur du tunnel, commune aux tubes. | float | `unit:M` / m | 1500 | {"bounds": {"min_exclusive": 0, "authority": "code"}} |
| `n_tubes` | Nombre de tubes du tunnel. | int | `unit:NUM` / nombre | 2 | {"bounds": {"min": 1, "max": 8, "authority": "code"}} |
| `n_lanes_per_tube` | Nombre de voies dans chaque tube. | int | `unit:NUM` / nombre | 2 | {"bounds": {"min": 1, "max": 6, "authority": "code"}} |
| `altitude_m` | Altitude du tunnel ; une ville ne fixe pas celle du site. | float | `unit:M` / m | 300 | {} |
| `max_depth_m` | Épaisseur maximale au-dessus du tunnel dans TLS. | float | `unit:M` / m | 80 | {} |
| `gradient_percent` | Pente longitudinale : 2 % correspond à 2 m par 100 m. | float | `unit:PERCENT` / % | 2.0 | {} |
| `tunnel_context` | Urbain, périurbain ou rural : modifie le modèle de trafic. | category | `None` / catégorie | peri-urban | {"values": ["urban", "peri-urban", "rural"]} |
| `lighting_type` | Technologie et commande, pas une intensité lumineuse en lux. | category | `None` / catégorie | LED adaptive | {"values": ["LED adaptive", "LED fixed", "mixed", "sodium fixed"]} |
| `ventilation_type` | Type de ventilation modélisé. | category | `None` / catégorie | longitudinal | {"values": ["natural/low ventilation", "longitudinal", "semi-transverse", "transverse"]} |
| `aux_kw_per_km_tube` | Puissance auxiliaire par kilomètre et par tube. | float | `unit:KiloW per km per tube` / kW/(km·tube) | 35.0 | {} |
| `base_fixed_kw` | Puissance constante ajoutée pour l'ensemble du tunnel. | float | `unit:KiloW` / kW | 40.0 | {} |
| `traffic_level` | Multiplicateur du trafic ; 1 est la référence, pas des véhicules/jour. | float | `unit:UNITLESS` / 1 | 1.0 | {} |
| `morning_peak_hour` | Heure centrale du pic de trafic, entre 0 et 24. | float | `unit:HR` / h du jour | 8.0 | {} |
| `evening_peak_hour` | Heure centrale du pic de trafic, entre 0 et 24. | float | `unit:HR` / h du jour | 18.0 | {} |
| `peak_width_h` | Durée caractéristique des pics de trafic. | float | `unit:HR` / h | 1.4 | {} |
| `traffic_sensitivity` | Coefficient du modèle, sans dimension. | float | `unit:UNITLESS` / 1 | 0.65 | {} |
| `noise_sigma` | Écart-type relatif du bruit ; 0,06 correspond à 6 %. | float | `unit:UNITLESS` / 1 | 0.06 | {"bounds": {"min": 0, "authority": "code"}} |
| `pollution_probability_per_day` | Probabilité par jour ; 0,05 = 5 %, pas un taux mesuré. | float | `unit:UNITLESS` / 1 | 0.05 | {"bounds": {"min": 0, "max": 1, "authority": "code"}} |
| `accident_probability_per_day` | Probabilité par jour ; 0,015 = 1,5 %. | float | `unit:UNITLESS` / 1 | 0.015 | {"bounds": {"min": 0, "max": 1, "authority": "code"}} |
| `pollution_sensitivity` | Coefficient de surcroît lié aux événements de pollution. | float | `unit:UNITLESS` / 1 | 0.55 | {} |
| `accident_sensitivity` | Coefficient de surcroît lié aux accidents simulés. | float | `unit:UNITLESS` / 1 | 0.75 | {} |

## experiment

| Champ | Définition | Type | Unité canonique / lisible | Défaut proposé | Contraintes déclarées |
|---|---|---|---|---|---|
| `start_date` | Premier jour simulé, au format AAAA-MM-JJ. | date | `None` / date | 2025-01-01 | {} |
| `n_days` | Nombre de jours effectivement simulés. | int | `unit:DAY` / jours | 7 | {"bounds": {"min": 1, "authority": "policy"}} |
| `freq_minutes` | Durée entre deux points de calcul. | int | `unit:MIN` / min | 60 | {"bounds": {"min": 1, "authority": "policy"}} |
| `n_runs` | Nombre de trajectoires Monte Carlo. | int | `unit:NUM` / nombre | 3 | {"bounds": {"min": 1, "authority": "policy"}} |
| `base_seed` | Graine pseudo-aléatoire pour reproduire le calcul. | int | `None` / identifiant | 42 | {"bounds": {"min": 0, "authority": "policy"}} |

## Sorties

Les quantités concernent tous les tubes. Les séries ne déclarent pas de fuseau horaire.

### representative.csv

Réalisation 0 au pas natif ; exemple de trajectoire, pas la médiane.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `season` | sans unité | Saison du calendrier simulé ; ne prouve pas une couverture annuelle. |
| `hour_int` | h | Heure du jour, de 0 à 23 ; pas une durée. |
| `dayofweek` | 1 | Indice : lundi 0, dimanche 6. |
| `day_type` | sans unité | Jour de semaine ou week-end du calendrier simulé. |
| `traffic_index` | 1 | Indice relatif de trafic ; pas un nombre de véhicules par jour. |
| `pollution_event` | 1 | Indicateur binaire d'événement de pollution simulé. |
| `accident_event` | 1 | Indicateur binaire d'accident simulé. |
| `lighting_kw` | kW | Puissance électrique calculée. |
| `ventilation_kw` | kW | Puissance électrique calculée. |
| `auxiliary_kw` | kW | Puissance électrique calculée. |
| `power_kw` | kW | Puissance électrique calculée. |
| `energy_kwh` | kWh | Énergie du pas : power_kw × freq_minutes / 60. |

### kpis.csv

Une ligne par réalisation sur toute la période simulée.

| Colonne | Unité | Sens |
|---|---|---|
| `run` | sans unité | Identifiant de réalisation Monte Carlo, à partir de 0. |
| `seed` | sans unité | Graine pseudo-aléatoire : base_seed + run. |
| `total_mwh` | MWh | Énergie de toute la période : somme des energy_kwh / 1000. |
| `annualized_mwh` | MWh/an | Extrapolation : total_mwh × 365 / n_days ; pas une année observée. |
| `peak_kw` | kW | Puissance électrique calculée. |
| `mean_kw` | kW | Puissance électrique calculée. |
| `load_factor` | 1 | mean_kw / peak_kw par réalisation ; sans dimension, 0,6 équivaut à 60 %. |
| `specific_kwh_m_year` | kWh/(m·an) | annualized_mwh × 1000 / length_m ; ensemble des tubes, par mètre de longueur du tunnel, pas par mètre-tube. |
| `n_pollution_events` | 1 | Nombre de transitions 0 vers 1 dans la série pollution_event ; un événement actif au premier pas n'est pas compté. |
| `n_accident_events` | 1 | Nombre de transitions 0 vers 1 dans la série accident_event ; un événement actif au premier pas n'est pas compté. |
| `base_seed` | sans unité | Graine de base fixe de l’expérience ; 42 par défaut, modifiable explicitement. |

### envelope.csv

Puissances moyennées par heure dans chaque réalisation, puis statistiques entre réalisations. p10/p90 sont des quantiles empiriques, pas un intervalle de confiance.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `median` | kW | Puissance électrique calculée. |
| `p10` | kW | Puissance électrique calculée. |
| `p90` | kW | Puissance électrique calculée. |
| `mean` | kW | Puissance électrique calculée. |

### season_profiles.csv

Puissance moyenne par saison et heure du jour, dans chaque réalisation, uniquement sur les jours simulés.

| Colonne | Unité | Sens |
|---|---|---|
| `season` | sans unité | Saison du calendrier simulé ; ne prouve pas une couverture annuelle. |
| `hour_int` | h | Heure du jour, de 0 à 23 ; pas une durée. |
| `power_kw` | kW | Puissance électrique calculée. |
| `run` | sans unité | Identifiant de réalisation Monte Carlo, à partir de 0. |

### daily.csv

Agrégation journalière de la réalisation 0 : somme de l'énergie et moyenne de la puissance ; pas une médiane Monte Carlo. Les dates suivent le calendrier sans fuseau déclaré.

| Colonne | Unité | Sens |
|---|---|---|
| `timestamp` | ISO 8601 | Horodatage sans fuseau horaire déclaré ; aucune localisation déduite. |
| `energy_kwh` | kWh | Somme des énergies des pas natifs de la journée, réalisation 0. |
| `mean_kw` | kW | Moyenne des puissances des pas natifs de la journée, réalisation 0. |

## Contrôles complémentaires

- Pinned and unchanged backend
- freq_minutes in 5,10,15,30,60
- n_days * 1440 / freq_minutes * n_runs <= 2000000
- peak_width_h > 0
- 0 <= morning_peak_hour, evening_peak_hour < 24
- Nonnegative max_depth_m, gradient_percent, aux_kw_per_km_tube, base_fixed_kw, traffic_level, traffic_sensitivity, pollution_sensitivity, accident_sensitivity

Ces contraintes du prototype ne constituent pas des limites de validité physique calibrées. Voir docs/agent-contract.md pour les règles d'interprétation et de restitution.
