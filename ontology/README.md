# Contrat sémantique TLS

- [tls-contract.json](tls-contract.json) : contrat lisible par machine, 26 paramètres, contraintes, unités, catégories, tâches, règles d'exécution et qualification des cinq tables numériques.
- [tls-scenario.schema.json](tls-scenario.schema.json) : structure d’un scénario complet, types, unités et acceptation.
- [tls-vocabulary.ttl](tls-vocabulary.ttl) : RDF/SKOS généré depuis le descripteur et les métadonnées des sorties. Définitions, types, bornes, défauts proposés, intentions et indicateurs ; classes et propriétés du projet explicites.
- [Référence des paramètres et sorties](../docs/tls-reference.md) : tableaux destinés à la lecture humaine.
- [Instructions pour les agents](../docs/agent-contract.md) : provenance, hypothèses, exécution Python sans Gemini et restitution.

Chaque calcul exporte un `semantics.ttl` avec la configuration, les unités, l'acceptation et les dérivations PROV-O, ainsi qu'un manifeste JSON complet. Les définitions sont générées, pas déduites par le LLM.

Ce contrat décrit le périmètre implémenté du prototype, pas une ontologie exhaustive de l'ingénierie des tunnels. Les bornes et les contrôles font autorité dans le descripteur et le code Python. Le graphe n'exécute aucun raisonnement OWL ni contrôle SHACL. Les jetons d'unités ne sont pas un alignement QUDT validé ; le namespace GitHub n'est pas enregistré à w3id. Les données sont synthétiques et non calibrées.
