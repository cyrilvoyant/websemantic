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

Le Vieux-Port a conduit à des questions mais pas à une demande de recherche web. Cette lacune est conservée comme observation. Les graphes ont passé leurs contrôles locaux, ce qui ne mesure pas leur utilité pour un LLM.

## Accès navigateur

Premier cas préparé TLS-P01 soumis le 6 octobre : ChatGPT sans compte répond avec une configuration et signale l'absence de Python ; Grok sans compte demande une inscription ; Claude connecté en conversation incognito atteint une limite de dépenses. Aucun de ces essais ne produit de calcul. Détails : browser-access-20261006.json. La collecte navigateur ne nécessite pas de clé API ; ces limitations ne constituent ni une comparaison numérique ni une mesure de l'apport ontologique.

## Pilote dédié effectivement collecté

Les 60 cas préparés ont été soumis à la CLI avec Gemini 3.5 Flash Lite, une session neuve par cas et une répétition. Messages prévus et routeur lexical figé conservés ; arrêt si aucune suite ne correspond à la question. Traces privées : work/prepared-pilot-20261006. Synthèse agrégée : prepared-pilot-20261006.json. Les références et les réponses numériques restent privées pour éviter de les exposer aux prochains agents.

81 appels d'interprétation : TLS 27, LQL 26, pyrcel 28 ; les appels documentaires supplémentaires ne sont pas inclus. Deux demandes TLS ont produit un calcul, aucune pour les deux autres profils. Ce décompte n'est pas un taux de réussite : certaines demandes attendent une clarification ou un refus. TLS : 122/123 champs attendus concordants dans l'état final, 123/123 entrées présentes avec l'unité attendue ; les champs communs d'une comparaison sont contrôlés dans chacun des deux scénarios. Les deux configurations exécutées concordent sur 26 champs chacune avec les références figées ; quatre vecteurs puissance/énergie comparés à des exécutions natives, nRMSD maximal 2,227e-8.

Limites observées : acceptations explicites rejetées par le contrôle de citation, comparaisons hors profil LQL/pyrcel, défauts opérationnels/scientifiques non acceptés dans certaines demandes. Réconcilier les attentes du corpus et les profils avant un score de réussite confirmatoire. Aucun résultat manquant n'est exclu du relevé.

## Contrôle des règles relationnelles

24 exemples construits, distincts du corpus préparé : dose totale, humidité/sursaturation et complétude d'un mode d'aérosols. Données et ontologie identiques, cibles SHACL relationnelles désactivées puis activées, sans inférence OWL. Détection : 0/12 incohérences avec les seuls contrôles individuels, 12/12 avec les règles relationnelles ; aucun des 12 contrôles cohérents rejeté. Preuves : run_relational_controls.py et relational-controls-20261006.json. Contrôle de mécanisme, sans preuve de bénéfice pour un LLM ni généralisation hors de ces exemples. 31 tests ontologie/SHACL passent.

## Parcours publié pour les trois logiciels

Six calculs réels, deux processus neufs par logiciel, depuis les fichiers indexés copiés sans métadonnées Git et sans installation du projet. Dépendances déjà présentes sur le même poste Windows : pas une reproduction indépendante. Conservation du scénario et des champs déclarés ; métadonnées couvrant 36 colonnes TLS, 14 LQL et 23 pyrcel, y compris identifiants et drapeaux. RMSD de répétition nul pour les colonnes numériques ; nRMSD non définie si référence nulle.

18 perturbations bloquées sans dossier de sorties : unité incorrecte, hypothèse non acceptée, accord sous forme de texte, champ manquant, définition modifiée et backend modifié, pour chaque logiciel. L'essai révèle le CSV d'atmosphère omis dans l'index pyrcel et le besoin de typer strictement les accords ; corrections précédant le lot retenu. Lot : work/portable-controls-20261006-release ; synthèse publique : portable-controls-20261006.json ; harnais : run_portable_controls.py. Les tentatives de montage précédentes restent archivées et ne sont pas comptées. Aucun appel LLM, aucune conclusion comparative fournisseur ou intervalle statistique tiré de ces cas construits.
