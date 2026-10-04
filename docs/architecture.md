# Architecture

Le chemin actuellement exécuté est : demande → interprétation structurée → état du scénario → contrôles Python → adaptateur → TLS → résultats qualifiés.

## Composants

| Composant | Responsabilité |
|---|---|
| Descripteur | Paramètres, définitions, unités, contraintes, défauts, tâches, présentation et référence du logiciel |
| Session | Valeurs fournies, preuves textuelles, conversions, hypothèses, acceptations et historique |
| Interprétation | Valeurs explicitement données et actions demandées, selon un schéma déclaré |
| Validation | Complétude, types, unités canoniques, bornes, catégories, origine, preuves, acceptation et conflits |
| Registre | Catalogue des environnements et chargement d’un adaptateur local déclaré |
| Adaptateur | Contrôles du backend, appel natif, tables de sortie et qualification scientifique |
| Export sémantique | Concepts RDF/SKOS, configuration, activité de calcul, révision logicielle et dérivations PROV-O |

Gemini interprète la demande avec le descripteur, le schéma, l’état courant et l’historique. Il ne calcule pas les indicateurs et ne décide pas seul d’une acceptation. Les actions proposées sont limitées ; l’accord nécessite un extrait affirmatif contrôlé localement. Les pages consultées sont des données documentaires, jamais des instructions exécutables.

## Contrôle du calcul

La validation retourne `execute`, `clarify` ou `refuse`. Elle ne complète pas les valeurs. Une unité est normalisée avant ce contrôle seulement si une règle déclarée et une preuve univoque permettent la conversion. Une citation présente ne prouve pas à elle seule la justesse de l’interprétation.

Les bornes portent leur origine : contrôle du code ou politique de l’expérience. Une borne logicielle ne constitue pas automatiquement une limite de validité physique. L’adaptateur TLS ajoute ses contraintes de pas temporel, volume, paramètres physiques et révision inchangée.

Les réglages `operational_default` portent une autorisation préalable explicite de la politique d’essai. Dans TLS, cette règle concerne uniquement la graine fixe. Les hypothèses physiques restent soumises à l’accord de l’utilisateur.

## Sorties et provenance

Les CSV conservent les calculs numériques ; le manifeste décrit chaque colonne, unité et agrégation. Le RDF relie le scénario utilisé, l’activité de calcul, le logiciel fixé et les tables produites. Les sources et acceptations sont associées aux paramètres concernés.

La couche de données commune est utilisée avec des descripteurs indépendants dans les tests structurels. Une intégration réelle de LQL ou pvlib reste à effectuer avant de conclure sur le transfert scientifique.

## Périmètre

Les formats disponibles sont YAML, JSON, JSON Schema et RDF/Turtle. L’export JSON-LD, le contrôle SHACL et l’alignement QUDT ne sont pas encore implémentés. Aucun serveur MCP ni ensemble de fonctions distantes n’est exposé par cette version.
