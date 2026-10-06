# Protocole de comparaison

Comparer l’interface dédiée et les agents généralistes pour TLS, LQL-Equiv et pyrcel. Distinguer l’accord des interprétations avec un exécuteur commun, l’utilisation autonome des logiciels et la découvrabilité des ressources. La réutilisation correcte par un agent constitue un résultat utile.

Apparier les conditions documentaires : B0 documentation native, B1 guide, B2 contrat scientifique, B3 relations sémantiques. B2 et B3 portent les mêmes faits ; préciser quels contrôles sont imposés par le logiciel et lesquels sont utilisés par l’agent. Le pilote comporte 20 demandes par logiciel ; la cible réservée est de 100 par logiciel, avec trois répétitions indépendantes, après examen du pilote.

Fixer révisions, environnement, outils, accès web, graines, grille temporelle et budget d’interaction. Conserver scripts, sources, accords et fichiers calculés. Séparer les essais de développement du corpus réservé ; regrouper les paraphrases d’un scénario. Faire annoter les références et arbitrer les désaccords avant l’évaluation.

| Objet | Mesure |
|---|---|
| Paramètres | Exactitude par champ après conversion ; tolérances déclarées |
| Hypothèses | Valeurs non justifiées, inconnues et conflits conservés |
| Décisions | Matrice execute/clarify/refuse |
| Vecteurs numériques | RMSD dans l’unité de la grandeur et nRMSD ; supports et réalisations alignés |
| Indicateurs | Erreurs absolues et relatives |
| Qualification | Accord du JSON et des explications avec les CSV et le manifeste |
| Réutilisation | Modifications du cœur et coût d’intégration |

RMSD = sqrt(mean((P − P_ref)²)) ; nRMSD = RMSD/sqrt(mean(P_ref²)). Une référence identiquement nulle rend la nRMSD indéfinie : conserver l’erreur absolue. Comparer sur la même grille et les mêmes graines, sans mélanger des paramètres de dimensions différentes.

Évaluer les explications par leurs affirmations soutenues et leur couverture : unités, période, hypothèses, origine et portée. Rapporter les effets et intervalles par scénario, y compris les résultats nuls ou défavorables.

La qualification lisible par machine est un résultat à contrôler : définition et unité de chaque sortie, support temporel, agrégation/transformation, origine, limites et lien à l’expérience/version. Vérifier schéma, résolution des champs et concordance avec les fichiers calculés. La sémantique définit les significations ; l’ontologie explicite les relations ; le contrat relie ces éléments aux contrôles et à l’exécution. Cette continuité constitue l’hypothèse distinctive à tester.

Ordre de collecte : arbitrer les références et les profils du pilote, puis comparer les interprétations en sessions neuves avec un exécuteur commun ; collecter ensuite l'exécution autonome B0/B3, puis le contraste B2/B3 à faits et outils appariés. Conserver les cas de qualificatifs, unités, sources et ambiguïtés ; ne pas remplacer les demandes préparées par des balayages numériques. Une panne d'outil ou de quota reste une limite d'accès, pas un résultat simulé. Les intervalles à 95 % se calculent par groupes de scénarios dans la campagne : ils ne sont pas une note de qualité du papier ni une preuve issue des contrôles construits.

FAIR pour les données et FAIR4RS pour les logiciels fournissent le cadre de réutilisation : métadonnées découvrables, ressources accessibles et versionnées, vocabulaires/interfaces déclarés, provenance, dépendances et licences. Documenter les lacunes ; ce relevé de preuves n’est pas une certification FAIR et ne démontre pas la validité scientifique des sorties.

Pour deux configurations, vérifier affectation des valeurs, accords, champs contrôlés, CSV individuels/réunis et écarts entre médianes. Une erreur partielle ne produit pas une comparaison achevée. Un écart entre configurations concerne l’ensemble des paramètres modifiés.

Les références numériques sont les calculs des trois logiciels sous configuration contrôlée, pas des observations de terrain. Une demande ambiguë peut admettre plusieurs réponses : définir les configurations admissibles avant de noter. Présenter séparément disponibilité des outils, réussite des tâches et erreurs numériques conditionnelles.

Plan détaillé : [campagne et intégration](plan-etude.md). Correspondance avec les demandes : [audit du manuscrit](audit-manuscrit-20261006.md). Qualificatifs : [règles et tableau](qualificatifs.md). La normalisation par RMS remplace la normalisation par moyenne du draft précédent ; conserver les conventions avec les métriques.
