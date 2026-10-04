# Tester le PoC dans PowerShell

La premiere version fonctionne en terminal. Aucune page graphique, aucune modification de TLS ou LQL-Equiv. Gemini interprete les messages; le calcul TLS reste local. Seul TLS est utilisable pour l'instant.

## Lancer sur cette machine

```powershell
cd C:\Users\cvoyant\Documents\websemantic\semantic-sim-layer
& .\.venv\Scripts\websemantic.exe chat --model tls
```

La variable utilisateur Windows GEMINI_API_KEY est lue sans afficher la cle, meme si le processus n'a pas encore recharge ses variables. Modele initial : gemini-3.5-flash-lite. Pas de plafond local par défaut ; les quotas du projet Gemini restent applicables. Pas de relance automatique ni de changement automatique de modele. L'historique de la session et le descripteur sont transmis a Gemini avec chaque phrase; ne pas saisir de donnees sensibles dans ce PoC.

## Parler naturellement

Le guide livré dans le package propose trois essais avec des phrases à copier. Par exemple : « Propose les valeurs manquantes sans les accepter », « Explique-moi la graine », « Montre le tableau des paramètres avec leurs unités », « Propose cinq questions pour affiner mon étude », puis « J’accepte les hypothèses proposées, lance le calcul ». Gemini propose les actions ; les opérations et le consentement sont contrôlés localement. « Prends le reste par défaut » reste une acceptation explicite et autonome du profil pour les champs manquants.

La recherche n’est pas systématique pour chaque phrase : elle se déclenche sur une demande documentaire explicite ou lorsque Gemini indique que des sources externes sont nécessaires. Les définitions du contrat restent locales. Les raccourcis ci-dessous sont facultatifs.

## Premier parcours

Saisir une phrase :

```text
Je veux estimer la consommation d'un tunnel periurbain de 2000 m, deux tubes et deux voies par tube. Le trafic est eleve.
```

Gemini extrait les donnees explicites et pose des questions. Le tableau local montre les inconnues. Pour un essai rapide, saisir ensuite les commandes locales :

```text
/profile
/accept
/run
/quit
```

`/profile` propose les valeurs manquantes d'un profil de demonstration et affiche le scenario. `/accept` accepte explicitement ces valeurs proposees, sans modifier les donnees deja extraites. `/run` revalide et calcule. Ce profil n'est pas un tunnel mesure. Il simule 7 jours de 2025 au pas horaire, avec 3 realisations et la graine 42. Son energie annualisee est une extrapolation 365/7, pas une annee simulee.

## Autres commandes

```text
/help
/show
/set inputs.traffic_level 1.2
/set experiment.n_days 365
/set inputs.lighting_type "LED fixed"
```

`/set` attend une valeur JSON dans l'unite canonique, represente une correction explicite acceptee et ne consomme aucun appel Gemini. Les commandes commencant par `/` sont executees localement. Un message naturel ne lance jamais une simulation automatiquement; utiliser `/run`.

Hors conversation :

```powershell
& .\.venv\Scripts\websemantic.exe models
& .\.venv\Scripts\websemantic.exe describe tls
& .\.venv\Scripts\websemantic.exe chat --once "Tunnel periurbain de 2000 m avec deux tubes"
```

Les sorties sont dans `runs/<identifiant>/` : CSV, manifest.json et conversation.json. Le manifeste est une premiere trace JSON; RDF/JSON-LD/SHACL et l'annotation detaillee par indicateur restent a implementer. Les commandes, l'API REST et les tests vivent uniquement dans le nouveau depot.

## Installation sur une autre machine

Cloner le nouveau depot avec ses sous-modules, creer un environnement Python puis installer `pip install -e ".[dev]" numpy pandas`. Le checkout est requis pour les descripteurs et le moteur epingle. Cette version n'est pas encore un package autonome de distribution; utiliser `--workspace <dossier-du-checkout>` si le package n'est pas installe en editable. Configurer sa propre cle hors Git.

## Limites

Correspondance de tache par Gemini vers les taches declarees, validation deterministe mais pas preuve semantique universelle, conversion exacte m/km uniquement pour longueur explicite, aucune execution de code genere. Les erreurs HTTP ne divulguent pas les corps ou en-tetes. Pas de streaming de reponse encore : le terminal attend le resultat complet de l'appel. Les garde-fous de calcul limitent jours, realisations et volume d'experience. Aucun gain scientifique n'est deduit des tests logiciels.

Les réponses présentent des phrases explicatives et un schéma textuel. /show donne la synthèse ; /details affiche tous les paramètres techniques. /run explique les résultats calculés, leur annualisation et leurs limites sans appel Gemini supplémentaire.

### Évolution prévue : conversation vocale
À terme : microphone -> transcription corrigible -> LLM -> validation locale -> calcul autorisé -> explication écrite et synthèse vocale. Les schémas restent affichés dans le terminal. Les nombres, unités et hypothèses restent soumis aux confirmations et contrôles du PoC textuel. La voix est une évolution prévue, non implémentée ; moteurs, coûts et traitement des enregistrements restent à définir.

## Qualification des résultats
Le document de Nicolas Fichaux (réunion du 2 octobre 2026) motive le lien entre besoin, information, données, provenance et adéquation à l'usage. Il ne fournit pas de nomenclature d'unités TLS. Celle-ci est vérifiée dans le code du simulateur figé.

Chaque `manifest.json` contient désormais `output_qualification` : signification et unité de chaque colonne CSV, agrégation, durée, pas de calcul, nombre de réalisations, périmètre du tunnel et usages admis ou exclus. L'absence de coordonnées et de fuseau horaire est explicite. Les hypothèses et incertitudes restent documentées dans le même manifeste.

| Grandeur | Unité | Interprétation |
|---|---|---|
| Puissance | kW | Valeur calculée au pas déclaré ; pic dépendant de ce pas |
| Énergie du pas | kWh | Puissance × durée du pas en heures |
| Énergie totale | MWh | Somme sur la période simulée |
| Énergie annualisée | MWh/an | Total × 365 / nombre de jours, sans correction saisonnière |
| Énergie spécifique annualisée | kWh/(m·an) | Tous tubes compris, divisée par la longueur du tunnel ; pas par mètre-tube |
| Facteur de charge | 1 (sans dimension) | Puissance moyenne / puissance maximale par réalisation |
| Trafic | 1 (indice relatif) | Pas un débit en véhicules/jour |

L'enveloppe p10–p90 est une dispersion empirique entre réalisations après moyenne horaire, pas un intervalle de confiance. La trajectoire representative est celle de la réalisation 0. Les profils saisonniers portent seulement sur les dates effectivement simulées. Avec trois réalisations, les quantiles restent peu étayés. Cette qualification est en JSON ordinaire, pas encore en RDF/JSON-LD ou SHACL.
