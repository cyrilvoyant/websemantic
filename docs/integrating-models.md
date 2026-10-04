# Ajouter un environnement scientifique

Le cœur commun ne contient plus de libellés, paramètres, villes ou indicateurs propres à TLS. Les sources des simulateurs restent intactes.

## Contrat d’intégration

1. Créer `descriptors/<environnement>/descriptor.yaml`. Déclarer `software`, `inputs`, `experiment`, `tasks.supported`, puis les métadonnées de présentation. Chaque champ a un type (`int`, `float`, `category`, `date`), une unité canonique éventuelle, ses bornes et, pour une catégorie, ses valeurs autorisées. Ajouter `label`, `display_unit`, `definition` pour les explications. Compléter `quantity_kind`, `model_component`, `scope_note`, `reference_implementation` et les alias pour distinguer quantité, rôle et limites.
2. Déclarer les défauts dans les champs avec `default` et une provenance `default_source` ou `profile.source`. Une hypothèse physique sans source et acceptation ne permet pas de calculer. Un réglage purement technique peut être marqué `operational_default` seulement avec une politique préalable explicite et `operational_default_source` ; cette exception ne doit pas servir à préaccepter une hypothèse scientifique. Les alias d’unités sont propres à chaque champ ; une conversion n’est exécutée que si `evidence_conversion` décrit les unités et facteurs et si la citation contient une valeur univoque.
3. Écrire un adaptateur relu dans `src/websemantic/adapters/`. Sa fonction `run(scenario, descriptor, workspace, output_root=None)` retourne `(dossier_resultats, indicateurs_medians)`. Elle appelle le backend intact, applique les contraintes propres au backend et produit `manifest.json`, avec au minimum `software` et `scenario` (dataclasses.asdict). Le contrôle commun est appliqué avant l’appel, et l’adaptateur peut le répéter à sa frontière.
4. Déclarer `runtime.adapter: websemantic.adapters.<module>:run`. Pour un backend Git embarqué, ajouter `runtime.backend_path` et `runtime.backend_marker`. Les points d’entrée viennent du descripteur local relu ; le LLM ne choisit ni import ni code à exécuter.
5. Compléter `presentation`: namespace, nom court, champs de résumé, suggestions et limites. Pour une table de résultats, `presentation.results` décrit son CSV, ses indicateurs `[colonne, libellé, unité]`, les champs de contexte et les notes. Les chiffres affichés proviennent des fichiers du calcul enregistré, même si la session a ensuite changé.
6. Ajouter l’environnement au catalogue de données `src/websemantic/environments.json` et passer `available` à true seulement après tests. Inclure ce JSON dans le package distribué. Aucun changement des modules communs n’est nécessaire pour enregistrer un nouvel adaptateur.

La recherche géographique est optionnelle. Le descripteur définit les lieux, URL, thèmes, champs proposés, contraintes et instructions du domaine. Sans catalogue, un nom de ville ne déclenche aucune hypothèse de contexte. La recherche documentaire générale reste accessible. `semantics.intent_indicators` définit les liens objectif/indicateur ; le vocabulaire RDF est construit depuis les champs du descripteur. L’adaptateur peut exporter sa qualification avec `export_semantics(scenario, qualification, dossier, descriptor)`.

Les règles locales qualitatives sont des données dans `interpretation.local_rules` : expressions à reconnaître, propositions, provenance et message. Elles ne créent pas de preuve terrain. Toute proposition non acceptée reste bloquée ; les choix explicites peuvent être préservés. Le périmètre scientifique et les limites du modèle doivent être revus par un spécialiste.

## Ce qui est déjà vérifié

Le même cœur traite deux contrats fictifs indépendants (dose et puissance), propose leurs defaults, normalise leurs alias, valide, appelle un adaptateur de test et exporte la provenance. Ces fixtures sont des tests structurels : elles ne constituent pas une intégration LQL-Equiv/pvlib ni une validation clinique ou photovoltaïque.

TLS est disponible. LQL et pvlib restent « Work in progress ». Le prochain transfert doit compléter leurs descripteurs et adaptateurs, puis mesurer les changements nécessaires par rapport à la révision du cœur retenue. Un gel formel n’est pas encore déclaré.

Une échelle `qualitative_scale` peut associer des expressions précises à une fraction d’une référence haute documentée. Déclarer ses alias, sa source et sa portée ; la conversion locale crée une hypothèse à valider. Ne pas généraliser cette échelle à des paramètres ou qualificatifs absents du descripteur.
