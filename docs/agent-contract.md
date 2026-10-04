# Exécuter TLS depuis un agent

## Accès

Commencer par [agent/README.md](../agent/README.md). Le fichier `agent/files.json` indique les sources et leurs empreintes. Lire les fichiers avec les outils web puis les écrire aux chemins indiqués dans l’espace Python. Ce parcours requiert numpy, pandas et rdflib ; le projet et Git n’ont pas besoin d’être installés.

L’adaptateur vérifie l’empreinte du module TLS exécuté, avec normalisation CRLF/LF, et conserve la méthode dans le manifeste. Un checkout présent ajoute les contrôles Git. La provenance par fichiers décrit un module correspondant à la révision publiée, pas un checkout authentifié.

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

## Réponse courte

Par défaut, afficher les trois médianes (énergie totale, énergie annualisée, pic), leurs unités, la période et le lien vers les fichiers. Indiquer brièvement « simulation ; annualisation extrapolée ». Conserver paramètres, hypothèses, sources, empreintes, versions et graines dans les fichiers de traçabilité. Donner les détails sur demande. Si le parcours exécuté diffère du parcours prévu, le signaler en une phrase et consigner les détails dans la note d’exécution.

## Lieu et contexte

Si une ville est citée, consulter les sources locales avec les outils web de l’agent. `geography` dans le contrat donne le catalogue des lieux, URL, champs proposés et règles utilisés par le dialogue local. Pour un autre lieu, rechercher des sources adaptées. Tracer URL, date, faits consultés et hypothèses dans `geographical_context.json` avec les résultats.

Conserver les caractéristiques explicites du tunnel. Pour « le même tunnel », conserver sa configuration ; proposer séparément les adaptations locales justifiées et demander leur acceptation avant de les appliquer. Une ville ne détermine ni la géométrie ni les probabilités d’événements. Si les sources manquent, conserver les hypothèses acceptées en le signalant brièvement. La date simulée détermine le facteur saisonnier ; le nom de ville seul ne modifie pas le calcul TLS.

## Suivi et comparaison

Le parcours détaillé est dans [agent/README.md](../agent/README.md). Le lanceur accepte deux scénarios complets et utilise le même orchestrateur que le dialogue local. Pour une suite d’étude, `--previous` conserve le lien au manifeste et trace les différences ; pas interne, réalisations et graine ne changent que sur demande explicite. Conserver les demandes pertinentes dans `request`, afin que les preuves restent exactes ; ne pas inventer de citations.

Un lieu connu cité dans la demande nécessite un contexte fourni par l’agent via `--context`. Pour un autre lieu, utiliser aussi `--place`. L’agent réalise la recherche avec ses outils web ; le lanceur vérifie les champs et l’acceptation, puis conserve le rapport. Ces contrôles ne prouvent pas la vérité des sources. Le format est décrit dans `agent/context.schema.json`.
