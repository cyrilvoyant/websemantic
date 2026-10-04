# Exécuter TLS depuis un agent

## Accès

Vérifier séparément lecture web/GitHub, récupération des sources, exécution Python et dépendances disponibles. Un échec Git ne suffit pas à conclure que la navigation est indisponible. Privilégier le clonage avec sous-modules ; conserver les révisions et les fichiers complets. Signaler toute ressource indispensable manquante avant le calcul.

## Contrat

Lire `ontology/tls-contract.json`, `docs/tls-reference.md`, `descriptors/tls/descriptor.yaml` et l’adaptateur `src/websemantic/adapters/tls.py`. Le format du scénario est défini dans `ontology/tls-scenario.schema.json` ; `examples/tls-complete.json` illustre une configuration acceptée.

- Conserver les noms, types, unités et catégories du contrat.
- Distinguer valeurs fournies, conversions, hypothèses et inconnues.
- Associer les valeurs fournies à un extrait de la demande ; documenter les conversions.
- Accepter un défaut ou une hypothèse seulement après accord explicite. Une question ou une négation ne vaut pas accord.
- Utiliser les échelles qualitatives déclarées comme conventions de simulation. Une valeur explicite reste prioritaire ; une ambiguïté demande une précision.
- Conserver URL, date et justification des sources consultées. Une commune, l’air ambiant ou des accidents routiers ne déterminent pas les probabilités d’événements TLS.

## Calcul

Appliquer `websemantic.core.validation.validate`, puis appeler l’adaptateur approuvé. Celui-ci contrôle les contraintes et la révision TLS `748e053e129669cf3e896d381e3c0ac01c763edd`. Conserver le backend intact et exécuter son calcul ; les formules explicatives ne le remplacent pas. Aucune clé Gemini n’est nécessaire pour cet accès Python.

Graine de base : 42 sauf demande explicite ; graine par réalisation : `base_seed + run`. Conserver le script, l’environnement, les traces et la révision WebSemantic.

Pour deux scénarios, valider chaque configuration et conserver les mêmes date, durée, pas, nombre de réalisations et graine. `websemantic.comparison.run` exécute les deux cas ; `ontology/tls-comparison.schema.json` décrit leur format.

## Restitution

Lire les CSV et `manifest.json`, notamment `output_qualification.tables`, avant de répondre. Donner en français les résultats essentiels, les unités, la période, les hypothèses et le dossier. Le JSON reprend les valeurs calculées, leur agrégation et les révisions.

- `kpis.csv` : indicateurs par réalisation ; les médianes viennent de ces lignes.
- `representative.csv` et `daily.csv` : réalisation 0 ; énergie journalière en kWh, puissance moyenne en kW.
- `envelope.csv` : quantiles horaires entre réalisations.
- `season_profiles.csv` : profils des saisons couvertes.

`annualized_mwh = total_mwh × 365/n_days` est une extrapolation en MWh/an. `specific_kwh_m_year` est en kWh/(m·an), tous tubes compris. Les horodatages n’ont pas de fuseau déclaré. Les sorties sont synthétiques ; les quantiles Monte Carlo décrivent les mécanismes simulés.

Une comparaison achevée a un manifeste `complete`, deux `scenario_runs` et aucun `INCOMPLETE.txt`. Les CSV réunis portent `scenario`. `comparison.json` donne les différences de médianes et le pourcentage relatif au scénario 2 (`null` si référence nulle). Des graines communes ne garantissent pas les mêmes tirages lorsque les paramètres changent leur séquence.

## Maintenance

`python tools/export_tls_contract.py` régénère contrat, vocabulaire, référentiel et exemple depuis le descripteur. Cette commande exécute un petit scénario pour inventorier les colonnes.
