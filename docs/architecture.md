# Architecture

Demande → état du scénario → validation → adaptateur → TLS → résultats.

| Composant | Rôle |
|---|---|
| Descripteur | Définitions, unités, catégories, contraintes, défauts et présentation |
| Interprétation | Extraire les valeurs et les actions du dialogue |
| Session | Conserver les preuves, hypothèses, accords et modifications |
| Validation | Vérifier complétude, types, unités, conflits et acceptations |
| Adaptateur | Contrôler la révision et appeler le backend intact |
| Export | Écrire CSV, qualification JSON et provenance RDF/SKOS/PROV-O |

Les chiffres viennent du simulateur. Les pages consultées servent de sources documentaires. Les hypothèses physiques demandent un accord ; la graine fixe suit la politique technique du descripteur.

Une comparaison conserve deux sessions et applique les modifications atomiquement. Les champs contrôlés sont identiques ; les deux appels restent séparés. Les CSV réunis gardent l’identifiant du scénario et les liens vers les sorties natives.
