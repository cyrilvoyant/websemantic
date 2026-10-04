# Dialogue

Ouvrez `WebSemantic.cmd` et choisissez TLS. Décrivez l’étude, précisez les choix, puis acceptez les hypothèses. Le calcul démarre si les contrôles sont satisfaits ; une modification explicite le relance. Le dossier des résultats apparaît après chaque calcul.

Exemples :

- « Propose les paramètres manquants. »
- « Montre le tableau : défaut, valeur retenue, unité et origine. »
- « Explique les formules utilisées. »
- « Propose cinq questions pour affiner l’étude. »
- « J’accepte les hypothèses, lance le calcul. »

Une question bloquante demande une réponse sur le choix concerné. La graine reste 42 sauf demande explicite ; elle figure dans les résultats.

## Raccourcis facultatifs

| Commande | Fonction |
|---|---|
| `/help` ou `/a` | Aide |
| `/s` | Cinq suggestions |
| `/show` | Résumé |
| `/d` | Tableau courant |
| `/details-all` | Tous les paramètres |
| `/e NOM` | Définition et unité |
| `/formulas` | Formules et coefficients |
| `/p` | Proposer les défauts manquants |
| `/v` | Accepter les hypothèses et calculer si admissible |
| `/web QUESTION` | Recherche documentaire |
| `/set GROUPE.NOM VALEUR` | Modifier en unité canonique, valeur JSON |
| `/r` | Calculer la configuration courante |
| `/q` | Quitter |

Les formes longues sont `/suggest`, `/details`, `/profile`, `/accept`, `/run`, `/quit`. Le préfixe `\` est aussi accepté.

## Deux scénarios

Nommez « scénario 1 » et « scénario 2 », les valeurs communes et leurs différences. « Même longueur » reprend une longueur déjà définie. Acceptez les hypothèses des deux cas avant le calcul.

Début, durée, pas, nombre de réalisations et graine sont communs. Les CSV réunis portent `scenario` ; les sous-dossiers conservent les calculs individuels. Les écarts concernent les configurations complètes. Redémarrez la conversation pour revenir à une étude simple.
