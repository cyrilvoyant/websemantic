# Référentiel scientifique

Définitions, unités, types, catégories, bornes et provenance des paramètres et sorties.

Espace de noms persistant : `https://w3id.org/websemantic/ns#` (préfixe `wsem:`). L’ontologie a pour IRI `https://w3id.org/websemantic/ns/core` ; un client RDF reçoit [core.ttl](core.ttl), un navigateur ce dossier, et `https://w3id.org/websemantic/ns/core/0.2.2` la version figée au tag `v0.2.2`.

Le [noyau](core.ttl) relie logiciels, tâches, paramètres, expériences, preuves et sorties. Les extensions [TLS](tls-vocabulary.ttl), [LQL-Equiv](lqlequiv.ttl) et [pyrcel](pyrcel.ttl) déclarent les concepts de domaine. Les [formes SHACL](shapes.ttl) contrôlent des contraintes individuelles et relationnelles ; les [questions de compétence](competency-questions.md) indiquent les relations à examiner. Lire une forme n'équivaut pas à l'exécuter : conserver séparément les traces des requêtes, des contrôles de graphe et de la validation Python.

[Définitions LQL](../docs/lql-contract-definitions.md) · [Définitions pyrcel](../docs/pyrcel-contract-definitions.md) · [Parcours Python](../agent/README.md)

## TLS

| Fichier | Usage |
|---|---|
| [tls-contract.json](tls-contract.json) | Contrat machine complet |
| [tls-scenario.schema.json](tls-scenario.schema.json) | Configuration d’un scénario |
| [tls-comparison.schema.json](tls-comparison.schema.json) | Deux configurations |
| [tls-vocabulary.ttl](tls-vocabulary.ttl) | Concepts et relations RDF/SKOS |
| [Référence TLS](../docs/tls-reference.md) | Définitions en tableaux |
| [Exécution](../docs/agent-contract.md) | Validation et restitution |

Les identifiants utilisent `ns#tls/`. Le graphe relie configurations, sources, versions, activités et fichiers selon SKOS et PROV-O. Les contrôles Python valident les configurations avant le calcul.

Le descripteur maintient les définitions. `python tools/export_tls_contract.py` régénère les documents. Les bornes logicielles et les conventions qualitatives gardent leur provenance et leur portée.

Les [qualificatifs](../docs/qualificatifs.md) définissent des hypothèses propres aux paramètres, avec source et accord. Le [plan de validation](../docs/plan-etude.md) sépare contrat plat et relations ontologiques.
