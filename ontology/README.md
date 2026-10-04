# Référentiel TLS

Définitions, unités, types, catégories, bornes et provenance des paramètres et sorties.

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
