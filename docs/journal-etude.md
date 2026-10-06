# Journal de l’étude

## 6 octobre 2026

Protocole et répartition proposés dans [le plan](plan-etude.md). Pilote distinct, corpus réservé, comparaisons numériques par grandeur et ablations guide/contrat/relations. LQL-Equiv-web et pvlib restent à intégrer et à valider ; aucune campagne comparative n’est déclarée terminée.

Les [conventions qualitatives TLS](qualificatifs.md) sont publiées avec leur autorité. Les traces de développement dans [qualifier-checks.json](../evaluation/qualifier-checks.json) testent les alias, unités, hypothèses et accords sans LLM ni calcul backend. Elles ne mesurent pas une performance conversationnelle. Reproduction : `python tools/check_qualifiers.py` dans l’environnement du projet.

Le tri-log de collaboration reste local. Ce journal publie les décisions et preuves techniques sans secrets ni échanges privés. Les futurs résultats comparatifs porteront leurs configurations, scripts, fichiers, versions et annotations, après clôture du corpus réservé.

## Accord de démarrage

Répartition et orientations validées par les deux collaborateurs. Le contrat sémantique et l’ontologie forment le cœur de la contribution. Pilote 20 par logiciel ; objectif final 100 réservés par logiciel, conditionné à la validation des références et au budget. Contrôle indépendant : LQL-Equiv-web public et sous-module partagent la révision dfc9a338205b8864b8e3470c4ae245b019e88844. Début des intégrations et de la modélisation dans des fichiers distincts, avec relecture croisée.

## Troisième domaine et distribution

Demande de remplacement éventuel de pvlib par un logiciel atmosphérique. Audit préalable documenté dans [troisieme-logiciel.md](troisieme-logiciel.md) : ecape-parcel-py cloné à révision fixe, licence MIT conservée, aucune exécution encore validée. Les logiciels originaux restent inchangés. Le package final doit inclure chaque nouveau backend, contrat, notice et exemple après vérification. Aucun nouveau package diffusé à ce stade.

## Connaissance préalable

Contrôle accepté : sessions neuves sans accès aux sources, assertions évaluées contre une version fixe. Le [protocole](connaissance-prealable.md) distingue familiarité et preuve de contamination. Banque de six questions rédigée hors du dépôt public, à relire avant collecte. Aucun modèle testé ni réponse fabriquée.

## Choix du candidat après tests

Deux installations isolées et deux calculs répétés réussis : ecape-parcel-py et pyrcel. Codex rejoint la recommandation de pyrcel 2.0.0 pour intégration. JAX CPU Windows fonctionnel dans cet essai ; fichiers, versions et limites dans evaluation/candidates. Pas de validation du pack ni d’activation du menu à ce stade.
