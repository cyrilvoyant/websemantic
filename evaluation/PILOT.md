# Première collecte de développement

Résultats : first-pilot-20261006.json et first-pilot-metrics.csv. Script : run_first_pilot.py. Les calculs et conversations détaillés restent dans work/first-pilot-20261006 ; le rapport identifie les calculs effectivement retenus. Aucun cas incomplet n’entre dans les métriques.

## Protocole conservé

- Trois logiciels : TLS, LQL-Equiv et pyrcel, sources originales inchangées.
- Pilote prévu : 20 demandes par logiciel, puis corpus réservé de 100 par logiciel si le pilote le permet. Le corpus réservé ne sert pas au développement.
- Demandes complètes, conversions, qualificatifs, ambiguïtés, modifications, comparaisons, lieux réels, qualification et limites. Les profils initiaux restent un cursus LQL et un mode pyrcel.
- Comparer configuration et décision avant les nombres. Conserver valeurs, unités, origine, preuve, acceptation, questions, sources et exécution.
- Comparaison numérique : paramètres/révision/grille/réglages identiques ; RMSD et nRMSD par grandeur. Référence nulle : nRMSD indéfini. Aucun score regroupant des unités différentes.
- Contraste documentaire : documentation native, guide agent, contrat plat, puis relations sémantiques/ontologiques. Même modèle et mêmes outils pour isoler cet effet. Les graphes ne sont pas encore une porte d’exécution.
- Parcours dédié et agents généralistes Python ; sessions vierges et trois répétitions prévues. Les interfaces sans Python sont classées par disponibilité des outils.
- Langage : couverture des éléments essentiels, affirmations non justifiées et qualifications ; double annotation sur un sous-ensemble, sans score lexical comme résultat principal.
- Recherche web séparée des références numériques figées. Une ville ou un ouvrage réel ne fournit pas automatiquement ses paramètres. Les hypothèses proposées exigent une validation.
- Familiarité préalable avec les logiciels mesurée sans sources ; métriques et configurations gelées avant collecte réservée.

## Lot réalisé

Neuf configurations numériques appariées et quatre demandes vagues avec Gemini, un échantillon chacune. Il ne s’agit ni de la campagne comparative ni d’une preuve d’apport ontologique. Les variables balayées sont trafic TLS, dose par fraction LQL et ascendance pyrcel. Le contrôle numérique appelle directement les API natives ; il ne simule pas un agent généraliste.

Le Vieux-Port a conduit à des questions mais pas à une demande de recherche web. Cette lacune est conservée comme observation. GPT, Claude, Grok et Perplexity restent non évalués ; leurs clés API ne sont pas configurées dans cet environnement. Les graphes ont passé leurs contrôles locaux, ce qui ne mesure pas leur utilité pour un LLM.
