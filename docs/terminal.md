# Utilisation du terminal

Ouvrez `WebSemantic.cmd`, puis choisissez TLS. LQL et pvlib sont en préparation. Décrivez l’étude en phrases ; aucun raccourci n’est nécessaire pour les exemples du guide.

## Dialogue

- « Propose les paramètres manquants sans les accepter. »
- « Montre les choix principaux avec leurs unités. »
- « Explique les options de ventilation. »
- « Propose cinq questions pour affiner mon étude. »
- « J’accepte les hypothèses proposées, lance le calcul. »
- « Passe la longueur à 2,5 km. »

Les informations explicites sont traitées avant une éventuelle acceptation. Une négation ou une question n’autorise pas les hypothèses. « Prends le reste par défaut » accepte le profil proposé pour les champs manquants ; ses valeurs restent des hypothèses de démonstration.

Un scénario complet et admissible est calculé après accord. Une modification explicite lance un nouveau calcul si les contrôles sont satisfaits. Une consultation ne relance pas une simulation. Le dossier des résultats est indiqué après chaque calcul.

## Détails

Le tableau courant présente les choix principaux. Demandez tous les paramètres pour afficher également les réglages techniques, ou demandez une définition par son nom français. La graine de base vaut 42 sauf modification explicite ; `base_seed` et `seed` restent dans les CSV et le manifeste.

La recherche documentaire s’active sur demande explicite ou si l’interprétation indique un besoin de sources externes. Elle n’est pas systématique. Les pages indisponibles sont signalées ; une source ne valide aucun paramètre et ne calibre pas le tunnel.

## Raccourcis facultatifs

| Commande | Fonction |
|---|---|
| `/s` | Cinq pistes d’affinement |
| `/d` | Tableau courant |
| `/details-all` | Tableau complet |
| `/e NOM` | Définition, unité et options |
| `/p` | Proposition des valeurs manquantes |
| `/v` | Accord sur les hypothèses et calcul admissible |
| `/web QUESTION` | Recherche documentaire |
| `/set GROUPE.NOM VALEUR` | Modification explicite en unité canonique, valeur JSON |
| `/r` | Demande de calcul |
| `/q` | Fin de la session |

Les commandes locales restent utilisables en cas d’indisponibilité du service conversationnel. Depuis le clone installé, `python -m websemantic.cli chat --direct --model tls` ouvre TLS directement ; sans `--direct`, le menu est affiché.

## Limites

L’interprétation conversationnelle utilise Gemini et les quotas du projet configuré. Il n’y a pas de plafond local par défaut ni de relance automatique après une erreur HTTP. La recherche publique peut être indisponible. Les comparaisons multiples se préparent en scénarios séparés. La transcription et la synthèse vocale restent des évolutions envisagées.

## Examiner et préciser l’étude

« Montre le tableau des défauts et des valeurs retenues » distingue le profil déclaré du scénario courant, avec les unités et l’origine. « Explique les formules utilisées » affiche les équations vérifiées et les coefficients des catégories retenues ; `/formulas` donne le même accès local. Les formules et leurs limites figurent dans le référentiel.

En cas de doute, le dialogue pose au plus deux questions ciblées. Une question bloquante survit à une simple consultation et à une acceptation globale ; il faut préciser le champ concerné. Une réponse courte à un niveau proposé est interprétée seulement dans le contexte de la question ouverte, puis reste une hypothèse à valider. Une question facultative aide à affiner l’étude sans bloquer un scénario déjà clair. Une recherche peut expliquer ce que les sources établissent et ce qu’elles laissent inconnu ; elle ne déduit pas une probabilité en tunnel des accidents recensés dans une commune.
