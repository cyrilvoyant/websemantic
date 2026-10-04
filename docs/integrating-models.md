# Ajouter un modèle

1. Créer `descriptors/<modèle>/descriptor.yaml` : logiciel, paramètres, expérience, tâches et présentation. Définir types, unités, catégories, bornes, sens et références.
2. Déclarer les défauts avec leur provenance. Réserver `operational_default` aux réglages techniques autorisés explicitement. Décrire les alias et conversions d’unités.
3. Écrire un adaptateur local `run(scenario, descriptor, workspace, output_root=None)` qui retourne `(dossier, indicateurs_medians)`. Valider puis appeler le backend intact ; produire les CSV et `manifest.json` avec logiciel, scénario et qualification.
4. Déclarer `runtime.adapter`, ainsi que le chemin et le marqueur du backend si nécessaire. Enregistrer le modèle dans `src/websemantic/environments.json` après vérification.
5. Définir les tableaux, indicateurs et notes dans `presentation.results`. Tester configurations, refus, unités et provenance.

Les échelles `qualitative_scale` associent une expression à une valeur typée ou une fraction d’une référence documentée. Elles proposent des hypothèses à accepter. `qualitative_policy` encadre les catégories, dates et identifiants.

Les lieux, sources et règles de contexte appartiennent au descripteur. Les imports exécutés viennent des adaptateurs locaux déclarés. Le vocabulaire et la provenance sont exportés depuis les définitions du modèle.
