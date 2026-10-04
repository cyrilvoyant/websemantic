# Référentiel sémantique

Le référentiel décrit les variables TLS et leur utilisation : définition, unité, type, catégories, bornes, composante du modèle, source d’implémentation et précautions d’interprétation. Les valeurs proposées sont distinguées des observations et des réglages techniques autorisés.

| Document | Usage |
|---|---|
| [tls-contract.json](tls-contract.json) | Contrat complet lisible par machine |
| [tls-scenario.schema.json](tls-scenario.schema.json) | Structure d’une configuration complète |
| [tls-vocabulary.ttl](tls-vocabulary.ttl) | Concepts, hiérarchie, relations et propriétés RDF/SKOS |
| [Référence TLS](../docs/tls-reference.md) | Paramètres et colonnes en tableaux |
| [Contrat d’exécution](../docs/agent-contract.md) | Règles d’interprétation, d’acceptation et de restitution |

Les identifiants de concepts sont propres à chaque modèle pour éviter de confondre des variables homonymes lors du rapprochement de graphes. Les identifiants TLS courants sont publiés dans `concept_identifiers` du contrat JSON ; ils utilisent le préfixe `ns#tls/`.

Le vocabulaire est organisé en paramètres d’entrée, réglages d’expérience et sorties. Il relie les intentions aux indicateurs et décrit les rôles dans le modèle. Chaque calcul associe sa configuration, l’activité d’exécution, la révision logicielle, les sources et les tables produites.

Les formats suivent les vocabulaires [SKOS](https://www.w3.org/TR/skos-reference/) et [PROV-O](https://www.w3.org/TR/prov-o/). Le namespace du projet n’est pas enregistré à w3id. Les jetons d’unité utilisés par le contrôle Python ne sont pas un alignement QUDT validé.

Le référentiel couvre le contrat actuel de TLS, sans prétendre décrire toute l’ingénierie des tunnels. Les contrôles Python font autorité ; aucun raisonnement OWL, contrôle SHACL d’exécution ou export JSON-LD n’est encore utilisé. Les bornes logicielles ne constituent pas une calibration physique.
