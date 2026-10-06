# Protocole de comparaison

Comparer l’interface dédiée, un agent avec le contrat WebSemantic et un agent avec le dépôt TLS natif. La réutilisation correcte par un agent constitue un résultat utile.

Fixer révisions, environnement, outils, accès web, graines, grille temporelle et budget d’interaction. Conserver scripts, sources, accords et fichiers calculés. Séparer les essais de développement du corpus réservé ; regrouper les paraphrases d’un scénario. Faire annoter les références et arbitrer les désaccords avant l’évaluation.

| Objet | Mesure |
|---|---|
| Paramètres | Exactitude par champ après conversion ; tolérances déclarées |
| Hypothèses | Valeurs non justifiées, inconnues et conflits conservés |
| Décisions | Matrice execute/clarify/refuse |
| Trajectoires | RMSD en kW et nRMSD par réalisation |
| Indicateurs | Erreurs absolues et relatives |
| Qualification | Accord du JSON et des explications avec les CSV et le manifeste |
| Réutilisation | Modifications du cœur et coût d’intégration |

RMSD = sqrt(mean((P − P_ref)²)) ; nRMSD = RMSD/sqrt(mean(P_ref²)). Une référence identiquement nulle rend la nRMSD indéfinie : conserver l’erreur absolue. Comparer sur la même grille et les mêmes graines, sans mélanger des paramètres de dimensions différentes.

Évaluer les explications par leurs affirmations soutenues et leur couverture : unités, période, hypothèses, origine et portée. Rapporter les effets et intervalles par scénario, y compris les résultats nuls ou défavorables.

Pour deux configurations, vérifier affectation des valeurs, accords, champs contrôlés, CSV individuels/réunis et écarts entre médianes. Une erreur partielle ne produit pas une comparaison achevée. Un écart entre configurations concerne l’ensemble des paramètres modifiés.

Les références numériques sont des calculs TLS sous configuration contrôlée, pas des observations de terrain.

Plan détaillé : [campagne et intégration](plan-etude.md). Qualificatifs : [règles et tableau](qualificatifs.md). La normalisation par RMS remplace la normalisation par moyenne du draft précédent ; conserver les conventions avec les métriques.
