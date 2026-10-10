# WebSemantic — plan de travail et d’évaluation

Version du 6 octobre 2026. Répartition et orientations validées. Contrat scientifique, sémantique et ontologie constituent le cœur du papier ; l’évaluation mesure leur apport. Aucun résultat comparatif n’est encore acquis. Taille finale et budget fixés après le pilote.

**Orientation validée après premiers essais : pyrcel 2.0.0 remplace pvlib pour le troisième domaine.** Voir [décision et preuves](troisieme-logiciel.md). Les paragraphes pvlib ci-dessous décrivent la proposition antérieure ; profils, métriques et textes seront harmonisés pendant l’intégration. LQL-Equiv-web reste le deuxième logiciel.

## 1. Question scientifique et périmètre

Question principale : à logiciel, données et moyens d’exécution constants, les contrats publiés améliorent-ils la traduction d’une demande en calcul vérifiable et en réponse correctement qualifiée ? Un agent généraliste qui réussit est un résultat favorable. L’objectif n’est pas de battre les agents, mais de rendre les logiciels utilisables par eux.

Trois applications : TLS, LQL-Equiv et un profil pvlib limité. Garder un cadre de data intelligence en introduction et en discussion ; le corps du papier reste une étude expérimentale de logiciel scientifique. Pas de grand modèle théorique ajouté pour donner de l’ampleur. Trois équations utiles suffisent : erreur numérique, normalisation, effet apparié. La reproductibilité du calcul n’est pas une validation physique ou clinique.

Les 100 scénarios sont proposés **par logiciel**, soit 300 cas indépendants, sous réserve de l’effort de validation mesuré au pilote ; repli proposé à 60 par logiciel. Ce choix conditionnel remplace la proposition intermédiaire de 100 au total consignée dans les échanges. Une requête, un scénario et une conversation ne sont pas synonymes : une étude peut nécessiter plusieurs messages. Les paraphrases et variantes dérivées restent dans le même groupe statistique. Cette taille est un objectif de campagne, pas une garantie de puissance statistique ; le pilote déterminera la précision accessible.

## 2. État de départ à préserver

- Le dépôt et le pack existants constituent la base. Archiver leurs empreintes, le guide et les versions avant toute modification. Les corrections d’installation non achevées restent identifiées comme telles.
- TLS est connecté ; les descripteurs LQL et pvlib ne déclarent encore que l’identité et le périmètre. Ne pas les présenter comme intégrés.
- Les sources originales sous external/ et les applications publiques existantes restent intactes. Les adaptateurs, contrats et exemples sont développés dans WebSemantic.
- LQL local est épinglé à dfc9a338205b8864b8e3470c4ae245b019e88844 : la branche main publique correspond à cette révision, vérifiée le 6 octobre 2026 par git ls-remote. Vérifier les conventions à cette révision avant intégration. Ne pas confondre une correction du backend et un effet du contrat.
- Le RDF/SKOS et la provenance existent pour TLS. Une véritable démonstration de l’effet des relations doit encore être construite : un graphe plus volumineux ne prouve pas une meilleure interprétation.

## 3. Répartition proposée

| Lot | Responsable proposé | Relecture | Livrable et validation |
|---|---|---|---|
| Intégration, packaging, CI, scripts d’évaluation | Développement | Sémantique et évaluation | Exécutions réelles, tests de non-régression et fichiers vérifiables |
| Ontologie commune et questions de compétence | Sémantique et évaluation | Développement + Cyril | Relations justifiées par des tâches et règles exécutables |
| Contrats TLS/LQL/pvlib | Développement pour l’API ; sémantique pour les définitions | Cyril pour le sens scientifique | Tableau API–concept–unité–origine–sortie, sans incohérence |
| Références de calcul | Développement | Sémantique et évaluation, indépendamment | Valeurs contrôlées et contrôles analytiques/métamorphiques |
| Corpus et grille d’annotation des phrases | Sémantique et évaluation | Développement + Cyril | Références avant les réponses candidates ; corpus réservé |
| Statistiques et ablations | Développement | Sémantique et évaluation | Analyse appariée, échecs inclus, intervalles par scénario |
| Manuscrit et guide | Première réduction ; relecture critique | Cyril décide | Texte court, résultats documentés, pas de revendications gratuites |

Cette répartition exprime des responsabilités. Chaque entrée du journal de suivi comporte demande, fichiers/version lus, modifications proposées, preuves, points en désaccord et prochaine action. Le second lecteur vérifie le livrable avant clôture. Les références privées ne sont pas publiées dans les dépôts consultés par les candidats.

## 4. Ordre d’exécution et portes de validation

### Lot 0 — Distribution fiable

Reprendre le problème d’installation séparément de l’évaluation des modèles. Définir les plateformes prises en charge. Tester sur Windows vierge sans Python/Git, compte non administrateur, chemins avec espaces et accents, dossier réseau, réinstallation et versions compatibles déjà présentes. Conserver l’erreur complète ; aucun message générique n’attribue un échec au réseau sans preuve. Vérifier démarrage, clé privée, un calcul et réouverture sans installation. Un package autonome ou un environnement géré est à comparer à l’installateur actuel avant choix. Une CI sur Windows propre complète les essais sur machine virtuelle ; nos postes de développement ne suffisent pas. Pas de nouvelle diffusion générale avant cette porte.

### Lot 1 — Figer le cœur, puis intégrer les deux domaines

Inventorier les dépendances TLS dans le cœur. Figer une révision de référence avant l’intégration LQL/pvlib, sans prétendre que les descripteurs d’identité constituent un test de transfert. Journaliser chaque modification ultérieure du cœur : fichier, motif, nombre de lignes et temps. Une correction nécessaire reste permise ; elle constitue un coût de transfert mesuré. Toute mise au point liée aux nouveaux domaines se déroule sur un corpus de développement, distinct des cas finaux.

**LQL-Equiv.** Profil initial : schémas fictifs, BED et équivalence au fractionnement de référence. Lire Course, Prescription, Options, bibliothèque des tissus et compute à la révision retenue. Décrire dose/fraction (Gy), nombre de fractions, dose totale et BED/EQD (Gy avec qualification), interruptions (jours), fractionnement et option de temps. Identifier explicitement organe, cible, paramètres bibliographiques et mode historique/courant ; ne pas proposer de valeur tissulaire arbitraire. Probabilités éventuelles : pourcentage ou fraction explicitement distingués, modèle et limites séparés. Commencer sans conseil pour un patient. Tests : référence à 2 Gy, fractionnement, interruptions, cours successifs, options temporelles, unités et paramètres incompatibles. Golden tests à cette révision et contrôles analytiques indépendants sont complémentaires.

**pvlib.** Profil initial : un système fixe, chaîne de modèles explicitement choisie, séries météo fournies et puissance/énergie AC/DC. Décrire latitude/longitude (degrés), fuseau et dates, inclinaison/azimut avec convention, irradiances (W/m²), température (°C), vent (m/s), module/onduleur, puissance nominale, pertes et modèles utilisés. Deux niveaux : fixture synthétique fixe pour comparaison numérique ; étude locale avec fichier météo téléchargé une fois, empreinte et source conservées. Ciel clair n’est pas météo observée. Tests : nuit, changement de fuseau, énergie intégrée, clipping, données manquantes, modèle thermique et catégories. Pas de prévision ni de modèle de stockage dans ce premier profil.

pvlib possède déjà un dépôt public. Inutile de forker son calcul pour obtenir un dépôt à nous : héberger notre adaptateur et nos contrats dans WebSemantic, en citant et épinglant pvlib. Un fork ne serait utile qu’en cas de modification du logiciel, ce qui n’est pas le projet.

Porte : adaptateur réel, contrat complet, références et sorties traçables, parcours dédié et agent disponibles. Activer chaque choix du menu uniquement après cette validation. Ajouter au guide un exemple linéaire et un exemple avec clarification pour chaque domaine ; guide court, détails dans les contrats.

### Lot 2 — Ontologie utile, pas décorative

Un noyau commun : Software, Task, Capability, Parameter, Quantity, Unit, Evidence, Assumption, Acceptance, Experiment, Execution, Output, Aggregation, ValidityLimit. Trois extensions de domaine. Réutiliser PROV-O pour les activités/sources et QUDT pour les grandeurs/unités ; SKOS pour les libellés/alias. Éviter des équivalences OWL fortes non démontrées. Le JSON, les tableaux et le RDF sont exportés d’une définition canonique, sans copies entretenues à la main.

Pour chaque champ : identifiant stable, définition courte, type, unité/dimension, alias, catégories, domaine admissible, autorité de la borne, défaut avec source, convention qualitative, état d’acceptation, variable API et sensibilité aux tâches. Pour chaque sortie : grandeur, unité, support spatial/temporel, méthode d’agrégation, transformation, origine synthétique, couverture de l’incertitude et limitations.

Questions de compétence obligatoires : « 2 km » vers quelle variable et unité ? Une moyenne journalière répond-elle à un pic instantané ? Une annualisation est-elle une année simulée ? Un nom de ville justifie-t-il un trafic ? Peut-on additionner ces sorties ? Quel fractionnement définit EQD ? Quelles données météo autorisent ce calcul AC ? Une borne numérique vient-elle du code ou de la physique ?

Chaque question a une réponse attendue, une règle/test et une trace concept → propriété → unité → API → source/acceptation → sortie. Les tâches relationnelles doivent utiliser le graphe ou des règles exportées de ses relations ; noter précisément quel mécanisme est actif. Une validation SHACL ajoutée ne sera pas qualifiée de raisonnement OWL. Déclarer les contrôles déjà réalisés en Python pour ne pas attribuer leurs effets à l’ontologie.

## 5. Références scientifiques et corpus

Créer, hors des sources offertes aux candidats, un dossier par scénario avec intention, messages autorisés, configuration ou décision attendue, hypothèses acceptées, sources figées, script de référence, CSV, manifeste et tolérances. Les agents ne voient ni résultats ni évaluateur. Deux lecteurs approuvent les références avant campagne ; les désaccords sont arbitrés et conservés.

Pour une demande incomplète, la référence est souvent **clarifier**, pas une valeur unique. Accepter un ensemble de configurations documentées quand plusieurs choix sont légitimes ; ne pas pénaliser une hypothèse différente mais valablement proposée. La comparaison numérique commence après fixation de la configuration et de son acceptation. Ajouter un test contrôlé qui donne directement cette configuration pour séparer erreurs de dialogue et erreurs d’exécution.

Répartition des 100 scénarios de chaque logiciel : 20 demandes complètes ; 15 conversions/paraphrases ; 15 manques et acceptation des défauts ; 10 ambiguïtés/conflits ; 10 modifications en conversation ; 10 comparaisons ; 10 qualification/agrégation ; 5 recherche et contexte ; 5 limites/refus. Pilote distinct : deux cas de chacune de ces neuf familles, plus deux cas complets, soit 20 par logiciel. Générer des valeurs nouvelles et des formulations françaises naturelles. Trois répétitions repartent d’un chat neuf ; les échanges prévus à l’intérieur du cas conservent leur contexte.

TLS : puissance au pas natif, énergie de période, profils/jours et composantes. Bordeaux et Puymorens servent à des tâches de contexte sourcé ; sans données propres au tunnel, les caractéristiques restent hypothétiques. Une documentation de l’ouvrage n’est pas une mesure de sa consommation. LQL : sorties par cours et par schéma ; pas de fausse série temporelle de puissance. PV : puissance AC/DC et énergie sur grille commune ; jeux météo fixes, nuits et fuseaux compris.

## 5 bis. Qualificatifs dans tous les essais

Inclure beaucoup, peu, faible, très fort, moyen quand déclaré, négations, comparatifs, valeurs explicites prioritaires, unités, catégories et réponses courtes après question ciblée. Pour chaque paramètre, une échelle documentée ou une règle de clarification est obligatoire. Pas de conversion universelle par pourcentage pour dose, météo, catégories ou probabilité. Les conventions numériques sont des hypothèses à accepter. Au moins 20 des 100 cas par logiciel mobilisent ce mécanisme, répartis dans les familles existantes (pas 20 cas ajoutés). Journaliser texte exact, concept/variable, niveau reconnu, formule/référence, valeur, unité, source, accord, clarification éventuelle et impact sur le calcul. Tester les alias déclarés automatiquement, puis des paraphrases et cas contradictoires indépendants dans le corpus réservé.

## 6. Conditions et campagne

**Pilote pratique.** Préférer les API lorsque disponibles ; température/version/options réellement exposées sont consignées. Chats web séparés avec mode/abonnement/outils enregistrés. Température zéro ne garantit pas le déterminisme.  Gemini, GPT, Claude, Grok et Perplexity, si accessibles : 60 cas × 5 services = 300 conversations pour une condition complète. Documenter service, identifiant/version du modèle lorsqu’exposé, date, abonnement, mode, Python, web, upload et budget. Tous ne possèdent pas les mêmes outils : vérifier leur disponibilité avant de comparer. Un chat sans Python peut être évalué pour configuration/explication ; son absence de calcul reste un résultat de disponibilité, pas une erreur RMSD. Ne pas appeler cela « tous les LLM du marché ».

**Campagne principale contrôlée.** Deux agents avec Python/web, GPT et Claude si ces moyens sont disponibles. 300 scénarios × 2 agents × 2 conditions (sources natives versus WebSemantic complet) × 3 répétitions = 3 600 essais. Même backend, mêmes données et budget pour les deux conditions ; seul le dossier/documentation offert change. Répertoires expérimentaux figés et séparation réseau contrôlée évitent que le bras natif consulte le contrat enrichi. Accès aux sites officiels et recherche web sont évalués séparément, avec requêtes/outils consignés ; leur évolution ne doit pas contaminer l’ablation contrôlée.

**Mécanismes.** Quatre niveaux : B0 sources/documentation natives ; B1 + guide agent ; B2 + contrat plat (paramètres, unités, schémas, provenance) ; B3 + relations ontologiques et règles de tâche. B1–B3 disposent du même garde d’exécution et des mêmes informations de base ; B2 conserve définitions et longueur comparables en retirant les relations. Si le garde est obligatoire dans toutes les conditions, B0 est explicitement un accès brut avec garde commun. Une variante véritablement native sans garde sera distincte. Réévaluer les 60 cas pilotes, avec B1 et B2 : 60 × 2 agents × 2 conditions × 3 = 720 essais supplémentaires, B0/B3 étant déjà couverts sur ces mêmes cas dans un lot dédié si nécessaire. Les cas pilotes ne sont pas recyclés comme données confirmatoires : annoncer cette ablation comme exploratoire ou créer 60 cas réservés homologues et ajouter leurs B0/B3 à son budget.

**Dédié versus généraliste.** Gemini dédié sur 300 × 3 = 900 essais. Une comparaison avec Claude/GPT mesure l’effet conjoint du modèle et du parcours. Pour isoler le parcours, ajouter Gemini généraliste avec les mêmes outils et contrat (900 essais), si accessible, ou un connecteur dédié du même modèle que l’agent. Ne pas conclure à un effet causal du seul add-on à partir d’un croisement de modèles différents.

Budget minimal indicatif : 300 pilote + 3 600 principal + 900 dédié = 4 800 conversations. Ablations supplémentaires et parcours apparié s’ajoutent ; aucun appel payant de masse ne démarre avant mesure du coût sur le pilote. Le budget réel inclut les messages de suivi, appels outils et recherches, pas seulement le nombre de conversations.

## 7. Mesures simples, séparées par objet

1. **Réussite de tâche**, critère principal : décision attendue, paramètres requis corrects/acceptés, exécution démontrée si attendue, sorties numériques dans tolérances et qualification essentielle correcte. Rapport par domaine, famille et condition. Les échecs d’installation, récupération, validation, exécution et réponse sont distingués.
2. **Paramètres** : proportion de champs exacts après conversion, catégorie/comptage exacts, configuration entièrement correcte, nombres de valeurs non justifiées et de défauts utilisés sans accord. Aucune RMSD entre mètres, Gy, heures et catégories.
3. **Numérique** : RMSD = sqrt(mean((y−y_ref)²)) dans l’unité du vecteur ; nRMSD = RMSD/sqrt(mean(y_ref²)) pour tous les domaines, dénominateur fixé avant campagne. Une référence identiquement nulle donne nRMSD non définie : publier RMSD/erreur absolue et réussite avec seuil absolu. Cette convention remplace la normalisation moyenne du draft précédent ; ne pas comparer des chiffres calculés selon les deux conventions. Rapporter également erreurs absolues/relatives de chaque KPI et erreur maximale. Pour LQL, vecteur de scénarios ou de cours d’une même grandeur, jamais concaténation BED/EQD/probabilités. Ne pas agréger directement kW et Gy. Alignement strict des dates, fuseaux, pas, seeds et réalisations ; pas d’interpolation pour cacher une grille incorrecte. Énergie : sommer P·Δt selon la convention du backend, non les valeurs sans le pas.
4. **Explications** : cinq éléments attendus (grandeur/unité, période ou protocole, hypothèses, origine des données, portée) ; couverture sur 5 et proportion d’affirmations vérifiables correctes. Erreurs graves explicites : résultat fabriqué, chiffre incompatible avec CSV, hypothèse présentée comme mesure, confusion énergie/puissance ou portée clinique. Un texte bref peut obtenir le meilleur score. Pas de BLEU/ROUGE principal, ni de score lexical censé démontrer une vérité scientifique. Un juge LLM peut préparer l’annotation ; double lecture humaine aveugle d’un échantillon stratifié et de tous les désaccords, avec accord inter-annotateurs, reste la référence.
5. **Traçabilité/effort** : configuration, sources/accords, versions/empreintes, script, fichiers et unités présents ; taux de reproduction par un second environnement, nombre de corrections du cœur, temps d’intégration, appels, durée et coût observés.

Les tolérances sont fixées par domaine et sortie après le pilote technique, puis gelées avant le corpus réservé. Tester mêmes versions et contrôle de flottants ; ne pas exiger une identité binaire entre plateformes si seule une tolérance numérique est justifiée. Une graine fixe permet une comparaison stochastique appariée, pas une preuve d’incertitude exhaustive.

## 8. Analyse et figures

L’unité indépendante est le scénario, pas chaque point temporel ni chaque affirmation. Conserver les trois répétitions pour estimer la variabilité des agents, puis résumer par scénario. Effets appariés : différence de réussite en points de pourcentage et différence de nRMSD, avec IC bootstrap à 95 % par groupes de scénarios. Un même tirage conserve ses répétitions et ses paraphrases. Rapport par logiciel avant moyenne interdomaines ; pondération explicite.

Un résultat sans fichier exploitable reste un échec ; RMSD conditionnelle aux seuls calculs disponibles est publiée avec son dénominateur. Aucun remplacement des échecs par zéro, aucun filtrage des refus ni conservation de la meilleure répétition. Résultats principaux : taux de réussite, erreurs de paramètres, erreurs numériques, qualification ; coût et analyses de langue secondaires. Préenregistrer les contrastes, ne pas chercher après coup celui qui améliore le résultat. Analyses multiples exploratoires identifiées ; pas d’inflation de précision en prenant 2 976 points pour 2 976 expériences.

Quatre figures utiles : schéma des trois parcours ; réussite et IC par domaine/condition ; distribution des nRMSD avec nombre de calculs manquants ; matrice des erreurs par famille. Un exemple TLS de courbe et de répartition énergétique illustre les sorties, sans remplacer les statistiques. Deux tableaux : contrats/domaines et résumé des résultats. Détails des scénarios, provenance et annotations en supplément.

## 8 bis. Calculateur serbe

Autorisé par Cyril comme ressource possible. Avant usage : identifier accès, ordonnanceur, quotas CPU/GPU et espace, disponibilité des conteneurs et réseau/API. Aucune connexion ni campagne distante n’est lancée sans ces informations. Utiliser la même révision et le même environnement verrouillé que les références locales ; un job par cas et reprise idempotente par trial_id. CPU suffisant a priori pour les profils bornés : mesurer temps/mémoire avant réservation. GPU seulement si un modèle local est ajouté ou si les mesures le justifient. Les chats web commerciaux ne deviennent pas parallélisables sur le cluster par simple ajout de CPU. Limiter la concurrence API et journaliser refus/quota/coût ; ne pas copier les clés dans GitHub. Un résultat local/cluster identique dans les tolérances précède la campagne.

## 9. Journal expérimental et confidentialité

Un enregistrement par essai : campaign_id, case_id, famille/groupe, domaine, condition, modèle/service/version, répétition, horodatage, moyens disponibles, révisions/empreintes, fichiers de données, prompt et transcript, décisions, paramètres/accords, sources consultées, script, CSV/manifest, erreurs, métriques, temps/coût, lecteur et verdict. Enregistrer l’état des sources web et la preuve de consultation ; pas de raisonnement interne privé demandé au modèle. La graine du simulateur est indépendante de la température/graine éventuelle du LLM. Secrets exclus des exports, conversations et dépôt public.

Les sites et applications natifs servent de références de logiciel/documentation. Si leurs résultats sont saisis manuellement, conserver inputs, captures et version ; privilégier les API Python identiques pour la référence numérique. Un échec de lecture du site, un échec Python et une réponse fausse sont trois événements différents.

## 10. Manuscrit et jalons

Réduire main.tex à introduction, méthode/contrat, applications et protocole, résultats lorsqu’acquis, discussion. Déplacer plan détaillé, inventaires, prompts et grilles en supplément. Conserver les équations des simulateurs dans leurs références ; ici seulement ce qui sert à l’évaluation. FAIR/data intelligence décrivent le contexte, pas une théorie générale démontrée. Toute phrase d’amélioration attend les comparaisons. Une ontologie n’est dite utile que si une ablation contrôlée montre ce qu’elle change.

Ordre : distribution fiable → cœur référencé → LQL → PV → contrats/relations → références et pilote → revue contradictoire dans le tri-log → gel protocole/corpus → campagne → statistiques → manuscrit final. Pas de calendrier promis avant mesure de l’effort et du coût. À chaque porte, publier état réalisé, tests exécutés, limites et décision de passer au lot suivant.

Sources de travail vérifiées : https://github.com/cyrilvoyant/LQL-Equiv-web ; https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/modelchain.html ; https://github.com/pvlib/pvlib-python ; https://www.w3.org/TR/prov-o/ ; https://qudt.org/ . Les benchmarks de reproductibilité des agents sont à discuter en travaux connexes, sans confondre correction de code et utilisation d’une API scientifique.
