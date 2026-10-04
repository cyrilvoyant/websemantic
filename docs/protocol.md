# Protocole de validation

Le protocole évalue la traduction d’une demande, la traçabilité du scénario et la réutilisation du code. Les sorties TLS constituent une référence de calcul sous configuration contrôlée, pas une observation de terrain. Aucun résultat comparatif n’est encore disponible.

## Conditions

| Condition | Accès et rôle |
|---|---|
| Interface dédiée | Dialogue WebSemantic, interprétation structurée, contrôles locaux et TLS |
| Agent avec contrat | Dépôt public avec définitions, règles, ontologie et sorties qualifiées ; script Python préparé par l’agent |
| Agent avec dépôt du modèle | Même tâche, code TLS et documentation native, sans enrichissement WebSemantic |

La réussite ne suppose pas que l’interface dédiée surpasse les agents : une exécution correcte grâce au contrat public constitue un résultat attendu de réutilisation. Utiliser les mêmes familles de modèles dans les conditions compatibles, ou signaler explicitement les facteurs confondus. Les ablations de provenance ou de relations sémantiques restent des analyses complémentaires à définir avant l’expérience.

## Corpus et environnement

Préparer un pilote de 20 à 30 demandes, puis un corpus réservé : demandes complètes, incomplètes, qualitatives, ambiguës, contradictoires, invalides et hors périmètre. Les paraphrases d’un scénario restent dans le même groupe. Les essais de développement déjà utilisés pour corriger le logiciel sont exclus du corpus réservé.

Définir avant les comparaisons les critères principaux, tolérances, budgets d’interaction et références admissibles. Deux évaluateurs examinent les annotations et arbitrent les désaccords. Une demande vague peut admettre plusieurs configurations ou une clarification ; elle ne doit pas recevoir une cible numérique artificielle.

Fixer les révisions des dépôts, l’environnement Python, les outils et la politique d’accès au web. Conserver les traces d’outils, les scripts exécutés, les paramètres, les sources, les accords et les fichiers produits. Distinguer variabilité de l’interprétation et variabilité Monte Carlo.

## Métriques

| Objet | Mesure |
|---|---|
| Paramètres | Exactitude par champ et par scénario, après conversion d’unités ; catégories et comptages exacts, tolérances numériques déclarées |
| Hypothèses | Affectations sans preuve ni hypothèse acceptée ; inconnues et conflits correctement conservés |
| Décisions | Matrice execute/clarify/refuse ; acceptations dangereuses et refus incorrects |
| Trajectoires | RMSD en kW et nRMSD par réalisation, sur la même grille temporelle et les mêmes graines |
| Indicateurs | Erreurs absolues et relatives séparées, avec traitement explicite des références nulles |
| JSON et qualification | Validité, complétude et exactitude contre le manifeste et les CSV, évaluées séparément |
| Explications | Part d’affirmations soutenues et couverture des éléments requis : unité, période, hypothèses, origine et limites |
| Transfert | Modifications du cœur, temps d’intégration et ajouts de descripteur/adaptateur après gel |

Pour une trajectoire de puissance, RMSD = sqrt(mean((P − P_ref)²)) et nRMSD = RMSD/mean(P_ref). Une moyenne nulle rend la nRMSD indéfinie ; conserver l’erreur absolue. Aucune interpolation ni association de graines n’est effectuée silencieusement. Ne pas calculer une nRMSD globale entre paramètres de dimensions différentes.

Comparer les résultats par scénario et conserver cette dépendance dans les intervalles de confiance et tests statistiques. La méthode sera choisie selon le type de résultat ; un test sur variables continues ne s’applique pas automatiquement aux décisions binaires. Rapporter aussi les résultats nuls ou défavorables.

## Reproductibilité

La graine de base est 42 sauf modification explicite. Chaque réalisation utilise base_seed + run. Vérifier `base_seed` et `seed` dans `kpis.csv`, ainsi que `base_seed` dans le manifeste. Une graine modifiée constitue un changement d’expérience. L’interface n’impose pas de renseigner ce réglage pendant le dialogue courant.

Le contrôle interne de répétition utilise la configuration acceptée et le backend fixé, sans nouvelle interprétation. Il est distinct de l’essai où un agent découvre le dépôt et construit son propre script.

## Portée

Les tests logiciels ne démontrent ni une meilleure utilisabilité ni la fidélité d’une consommation réelle. Le transfert LQL/pvlib demande des intégrations scientifiques effectives ; les contrats fictifs ne suffisent pas. Le protocole sera figé avant les comparaisons réservées et ses écarts seront consignés.

## Essais de comparaison de configurations

Inclure des demandes de deux scénarios et leurs clarifications : paramètres communs, différences correctement affectées, longueur du second inconnue, équipement décrit seulement comme ancien, accords et modifications ciblés. Vérifier que les deux configurations sont validées avant le calcul, que les champs contrôlés sont identiques et que chaque ligne CSV garde son identifiant de scénario. Les résultats individuels doivent correspondre exactement aux lignes réunies. Contrôler les écarts contre les médianes des CSV, les références nulles et l’absence de résultat achevé après un échec partiel.

Une comparaison entre configurations ne constitue pas un test causal d’un seul paramètre lorsque plusieurs champs changent. Les graines sont communes ; documenter les changements de séquence aléatoire possibles. Ces essais de développement restent hors corpus réservé.
