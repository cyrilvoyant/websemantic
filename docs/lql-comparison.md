# Comparer des schémas fictifs

`python agent/run.py lql examples/lql-comparison.json`

Le document contient `task: "compare_schedules"` et `schedules`, une liste de deux schémas ou plus. Chaque élément contient un `id` unique et un `scenario` complet au format de `examples/lql-complete.json`. Tous les schémas passent le validateur avant le premier calcul. L'organe à risque et la dose de référence doivent être identiques ; chaque valeur conserve unité, origine, source et accord.

Sans autre sélection, la cible doit être identique. Pour plusieurs cibles, ajouter `targets`, un enregistrement de paramètre dont `value` est une liste de noms exacts de la bibliothèque, `unit` vaut `null`, `origin` vaut `assumption`, `source` explique la sélection et `accepted` vaut `true`. Pour un groupe, remplacer `targets` par `anatomical_group`, avec la même structure et une clé du descripteur (`thoracic`, `head_and_neck`, `central_nervous_system`, `pelvis`, `abdomen`, `skin`). Le groupe sélectionne les cibles, jamais l'organe à risque. Un groupe sans cible est refusé.

`indicators.csv` conserve une ligne par schéma et cible. `comparisons.csv` contient chaque paire pour chaque cible : `left_dominates`, `right_dominates`, `equivalent`, `tradeoff` ou `indeterminate`. Les écarts TCP et NTCP sont en points de pourcentage, gauche moins droite. La dominance exige TCP supérieur ou égal et NTCP inférieur ou égal, avec au moins une inégalité stricte. Une probabilité absente interdit le verdict ; aucun classement global des cibles n'est construit.

Le manifeste conserve le document accepté, les définitions et les chemins des calculs individuels, avec leurs paramètres natifs, drapeaux de validité et traces sémantiques. Cette comparaison de simulations fictives n'est pas une recommandation clinique.
