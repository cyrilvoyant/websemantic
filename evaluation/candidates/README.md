# Faisabilité initiale des candidats atmosphériques

Essais locaux du 6 octobre 2026. Deux environnements Python isolés sous Windows, installations par wheels, sources originales clonées aux révisions indiquées dans les rapports. Aucun logiciel original modifié. Les dépendances sont détaillées dans les rapports ; pip check passe dans les deux environnements.

| Candidat | Cas synthétique répété deux fois | Résultat | Décision |
|---|---|---|---|
| ecape-parcel-py | Profil vertical de 57 niveaux, sans entraînement, pseudoadiabatique | Finite, différence max de répétition 0 | Alternative conservée |
| pyrcel 2.0.0 | Parcelle 30 s, pas de sortie 5 s, aérosol sulfate 10 classes | 7 instants, finite, différence max de répétition 0 | Retenu pour intégration |

Le choix est scientifique et pratique, pas une conclusion sur les données d’apprentissage. pyrcel permet un profil temporel, des distributions d’aérosols et une sémantique de paramètres utile au transfert. Claude recommande ce candidat ; Codex confirme sa faisabilité initiale sur CPU Windows. BSD-3-Clause : notices conservées lors de l’intégration.

Rapports et CSV sont des sorties de smoke tests, pas des références cliniques, une validation physique, un benchmark LLM ni un test d’installation sur Windows vierge. Un seul cas par logiciel ne prouve pas la robustesse. Essais de limites, unités, profils longs, distribution et Linux restent requis.

Pour reproduire le script, matérialiser `ecape-parcel-py` et `pyrcel` dans son dossier, aux SHA des rapports, puis l’exécuter avec un environnement correspondant et l’argument ecape ou pyrcel. pyrcel est exécuté avec JAX_ENABLE_X64=true et JAX_PLATFORMS=cpu. Le script importe les sources clonées ; les packages installés fournissent les dépendances. Les installations isolées, tentatives avant installation achevée et essais finaux sont distincts : seules les sorties finales réussies figurent ici.

Correction du 6 octobre : index temps pyrcel conservé en time_s (s), scénarios explicites et unités par colonne ajoutés aux rapports. Calculs répétées à nouveau ; aucun écart entre répétitions. Les coordonnées verticales ecape et le temps pyrcel restent distincts.
