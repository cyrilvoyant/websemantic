# Contrôle de connaissance préalable

Objectif : mesurer la familiarité observable avec le logiciel avant accès à ses sources. Ce contrôle ne démontre ni présence ni absence dans les données d’apprentissage.

## Conditions

Un nouveau contexte par question, sans historique fourni, web, fichiers, connecteur GitHub ni outil de récupération. Tracer modèle/service/version déclarée, date et outils effectivement désactivés. Si le service ne permet pas de vérifier ces restrictions, classer la condition « non contrôlée ». Aucun extrait, réponse de référence ou correction n’est fourni. Les essais principaux utilisent ensuite d’autres sessions neuves ; ce contrôle ne devient pas leur préambule.

Les réponses de Codex dans la conversation de développement ne sont pas un essai aveugle : le dépôt a déjà été consulté. Tester dans des sessions indépendantes seulement. Distinguer information présente dans le prompt, mémoire fournie par le service et connaissance préalable supposée.

## Questions et lecture

Petite banque privée, identique entre modèles : identité et fonction ; API et arguments ; unités/conventions ; dépendances ; exemple minimal sans exécution. Ne pas demander de valeur de simulation et ne pas prendre une bonne réponse comme preuve d’exécution. Un refus ou « je ne sais pas » reste une réponse, pas une faute scientifique.

Vérifier les assertions contre la révision retenue. Catégories séparées : connaissance générale du domaine, identité du logiciel, particularités de l’API, convention d’unité/version. Pour chaque assertion : correcte, incorrecte, invérifiable ou absence de réponse. Rapporter nombre correct et dénominateur, couverture des faits de référence et erreurs affirmées. Ne pas mesurer une similarité textuelle. Un résultat faible ne prouve pas l’absence du dépôt dans l’apprentissage ; un résultat élevé peut venir d’une connaissance générale, d’une autre version ou d’une documentation antérieure.

Faire approuver les faits de référence avant réponses candidates. Les références restent dans benchmark-reserve pendant la collecte, puis sont publiées avec réponses et traces. Date, versions et empreintes empêchent de qualifier d’hallucination une différence de version non vérifiée.

## Articulation avec les ablations

Ce contrôle est descriptif et séparé du critère principal. Les contrastes avec/sans contrat utilisent le même modèle, mêmes moyens, sources et budget, sur des scénarios inédits et références réservées. Un logiciel ne sera pas choisi parce qu’un seul modèle semble l’ignorer. Les profils proposés par ecape-parcel-py restent à valider techniquement et scientifiquement.

Aucun appel multi-fournisseur n’est lancé par la création de ce protocole ; le coût est ajouté au budget du pilote. Le nombre de questions est fixé avant collecte. Consigner dans chaque enregistrement prompt exact, réponse brute, contexte contrôlé ou non, outils, abstention, assertions, références, annotation et lecteur.
