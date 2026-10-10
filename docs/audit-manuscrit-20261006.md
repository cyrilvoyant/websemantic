# Audit du manuscrit et des demandes

Relecture du tri-log jusqu'à l'entrée de correction du scoring de 18:00, du plan d'étude, du protocole, de la grille d'annotation et du manuscrit. Références rédactionnelles lues localement : `Documents/EMS/paper/main.tex` et `protocol.tex`, `Documents/Stat_Dep/main_clean.tex`. Leurs résultats, auteurs et normalisations numériques ne sont pas transférés à cette étude.

Le draft existant `Documents/websemantic/main.tex` a été repris en place. Sa version antérieure reste dans `archives/main-avant-restructuration-20261006.tex`. La rédaction suit introduction, méthodologie, résultats, discussion et conclusion. Le détail du projet reste dans les documents et le tri-log ; aucun fichier réservé ni backend original n'a été modifié.

## Correspondance

| Demande ou décision conservée | Emplacement dans le draft ou le dossier | État |
|---|---|---|
| Le contrat, la sémantique et l'ontologie constituent le cœur | Méthodologie / Scientific contract ; figure du contrat | Central ; contrôle Python, graphe et SHACL distingués |
| Définitions, unités, bornes et leur autorité, catégories, défauts, preuve et accord | Scientific contract ; descripteurs et ontologies | Conservé ; pas d'assimilation défaut/mesure |
| Sorties qualifiées, provenance, support et agrégation | Scientific contract ; Evaluation metrics | Conservé ; pic/moyenne et annualisation explicités |
| Data intelligence, avec perspectives Earth et médicales | Introduction et domaines étudiés | Cadrage, sans grand modèle théorique |
| Trois logiciels, sans toucher aux dépôts originaux | Software and reference calculations | TLS, LQL-Equiv, pyrcel ; remplacement de pvlib validé dans le tri-log |
| Mesurer le transfert et les changements nécessaires au cœur | Scientific contract | Coût à mesurer ; aucune affirmation de zéro changement |
| Un LLM généraliste qui réussit est un résultat favorable | Introduction, Software use, Discussion | Conservé ; l'étude ne vise pas à battre les agents |
| Lire les fichiers utiles et exécuter le code, sans imposer Git | Software and reference calculations ; Interaction | Git n'est pas un prérequis |
| Comparer les interprétations de plusieurs LLM | Interpreter agreement | Rétabli explicitement : configurations/decisions, puis exécuteur commun |
| Distinguer absence de Python et erreur d'interprétation | Interaction ; Evaluation metrics ; Browser access | Modalités sans compte/connectées/API séparées |
| Gemini dédié versus agents généralistes | Software use | Conservé ; modèle et parcours non confondus causalement |
| Sources natives / guide / contrat plat / relations | Conditions B0–B3, tableau | Conservé ; accès croisé exclu dans les ablations contrôlées |
| Recherche depuis les sites officiels et dépôts, avec/sans URL | Discoverability et contexte | Volet exploratoire explicitement rétabli ; dix requêtes proposées |
| Contrôler la connaissance préalable | Corpus / familiarity | Sessions séparées sans sources ; aucune inférence sur les données d'apprentissage |
| 20 pilotes par logiciel puis objectif de 100 par logiciel | Corpus | 60 pilotes ; cible réservée 300, repli 60/domaine conditionnel |
| Trois répétitions et conversations vierges | Interaction ; Interpreter agreement ; Software use ; Analysis | Présent ; le lot mesuré n'a qu'une répétition |
| Cas complets, conversions, manques, conflits, modifications, comparaisons, qualification, contexte, limites | Corpus | Neuf familles, allocation des 100 cas conservée |
| Beaucoup, peu, faible, fort… pour chaque variable | Scientific contract ; Corpus | Mapping propre au paramètre ou clarification ; ≥20 cas qualitatifs/100 par domaine |
| Négations, chiffres prioritaires et réponses courtes | Corpus et interprétation qualitative | Conservé ; aucune échelle numérique universelle |
| Questions/clarifications et accords avant calcul | Interaction ; suites scriptées | Neuf suites ; routeur figé, questions non appariées conservées |
| Géographie ouverte, pas seulement Ajaccio | Geographical requests | Ajaccio, Montpellier, Paris, Bordeaux, Puymorens, Vieux-Port ; sources et mapping exigés |
| Pollution, accidents, trafic et pics locaux | Geographical requests | Hypothèses sourcées, non valeurs automatiques de ville |
| Connaissance du modèle autorisée comme proposition | Geographical requests | Hypothèse non sourcée ; jamais présentée comme recherche effectuée |
| Comparer deux scénarios et garder les sorties distinctes | Metrics et challenges | Champs communs contrôlés dans les deux états ; défis hors profil gardés |
| Comparer puissance native/énergie et EQD, sans mêler les dimensions | Software ; Metrics | RMSD/nRMSD par grandeur, grille et réglages identiques |
| nRMSD simple et reproductible | Équations 1–2 | Dénominateur RMS de référence ; zéro → NA ; aucune reprise du nRMSE moyen du papier EMS |
| Accord entre LLM, pas seulement accord adaptateur/backend | Interpreter agreement | Configurations identiques et dispersion pairwise, médiane/IQR |
| Peu de métriques de langage | Language assessment | Couverture de cinq éléments + assertions soutenues ; pas de score lexical principal |
| Double annotation sur 20 % et désaccords | Metrics ; annotation-grid.md | Précision ajoutée : première lecture de toutes les explications, seconde sur 20 % stratifiés + anomalies |
| Scénario comme unité statistique, pas les milliers de points | Paired analysis, équation 3 | Groupes avec répétitions/paraphrases ; IC bootstrap 95 % |
| Tous les essais tracés, échecs compris | Analysis ; Results ; tri-log | Aucun meilleur essai choisi ni échec remplacé par zéro |
| Courbes été/hiver, séries journalières et répartition énergétique | Geographical requests | Illustrations prévues ; ne remplacent pas les résultats statistiques |
| Calculateur serbe si nécessaire | Analysis and reproducibility | Ressource optionnelle, conditionnée à une reproduction vérifiée |
| Pack simple avec les trois environnements, guide court, clé privée | Travail de distribution et guide, hors corps scientifique | Demandes maintenues ; pas de nouveau test d'installation revendiqué par cette édition |
| Voix/transcription comme évolution | Historique et feuille de route du projet, hors expérience actuelle | N'est pas présentée comme implémentée ou comme résultat du papier |
| Sobriété, rédaction proche des articles de Cyril | Structure et réduction du main | Méthode avant résultats, trois équations utiles, deux tableaux et un schéma |

## Ce que l'audit a trouvé

La version précédente conservait l'essentiel du protocole, mais ne rendait plus explicites l'expérience d'accord entre interprètes avec exécuteur commun ni la découvrabilité sans URL. Ces deux volets sont rétablis. Les règles de budget, de connaissance préalable, de qualitatifs et de contexte ont été précisées, sans ajouter de résultat comparatif.

Les tests de développement, les incidents d'installation, les coûts détaillés et l'historique des corrections sont condensés dans le corps et restent dans les preuves/documents. Le nombre 60 désigne le pilote collecté ; les 300 scénarios, répétitions supplémentaires et contrastes documentaires demeurent une conception expérimentale. Aucun résultat de fournisseur n'est fabriqué.

La différence entre configurations admissibles n'est pas automatiquement une erreur : chaque complétion acceptée possède sa référence native ; la dispersion entre agents est une autre mesure. Les champs partagés sont contrôlés dans chaque scénario. Les réponses non applicables gardent NA et leur dénominateur. Ces précisions évitent de confondre créativité légitime, faute d'interprétation, défaut d'outil et erreur numérique.

Le renforcement de la première annotation de langage est une précision de méthode, pas une mesure déjà réalisée. Les références scientifiques et l'adéquation des profils restent à arbitrer avant une campagne confirmatoire.
