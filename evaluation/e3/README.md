# E3 — choix du code et preuves d'utilisation

Banc local, sans appel fournisseur. Les demandes, réponses et captures restent dans `benchmark-reserve/e3/` ou `work/`, jamais dans le dépôt public. Les tests sont des fixtures synthétiques, pas des résultats.

## Deux expériences distinctes

**E3-web** : même demande, session neuve, sans lien ou avec les deux liens (dépôt officiel et WebSemantic). Relever les capacités réellement disponibles : navigateur, téléchargement, Python, installation et accès réseau du moteur Python. Le point d'entrée est observé ; il n'est pas assigné. Une source citée ne prouve pas qu'elle a été ouverte. L'absence de trace signifie « non observé », pas « non utilisé ».

**E3-fichiers** : candidats figés, même contenu scientifique, avec/sans les seuls fichiers de citation, CodeMeta et Zenodo. `prepare` copie les fichiers explicitement sélectionnés et enregistre leurs empreintes sans toucher aux originaux. Contrat LLM, ontologie et guide restent identiques entre les deux conditions : leur retrait serait une autre intervention. Les noms neutres des dossiers ne garantissent pas l'anonymat des contenus. Anonymisation éventuelle : protocole et audit distincts avant les essais. Aucun miroir public créé par ce banc.

## Enregistrement avant collecte

Claude et Codex doivent figer : cas (TLS, LQL, pyrcel), demandes exactes, références exécutées/versions/tolérances, modèles/versions, outils, répétitions, ordre contrebalancé des conditions et candidats, limites de temps, arrêt fournisseur, règle de nouvelle session et code d'analyse. Conserver chaque échec/refus/limitation. Les concurrents doivent être sélectionnés pour une capacité comparable, avec vérification licence et périmètre ; aucune liste opportuniste après résultat.

Les prompts E3-web ne mentionnent pas une préférence pour WebSemantic. Deux URL exposent deux possibilités, sans forcer le choix. Les fichiers FAIR publics ne sont pas manipulables par l'observateur : cette expérience ne peut pas estimer causalement leur apport.

## Préparer et scorer

Le JSON privé de préparation contient `cases` et `candidates`. Chaque cas contient `id`, `request`, `official_url`, `websemantic_url`, puis `reference_outputs` : `{quantity, unit, support, values}` et `absolute_tolerance` (zéro par défaut). Le support doit décrire période, pas, agrégation et alignement ordonné des valeurs. Chaque candidat contient `id` alphanumérique neutre, `root`, `scientific_files`, `fair_files`. Sélection explicite de fichiers publics uniquement : aucune clé, aucun paquet privé.

```powershell
python evaluation/e3/bench.py prepare ..\benchmark-reserve\e3\registration.json work\e3-frozen
python evaluation/e3/bench.py score ..\benchmark-reserve\e3\observation.json ..\benchmark-reserve\e3\case.json ..\benchmark-reserve\e3\artifacts work\e3-score.json
```

L'observation contient `id`, `case_id`, `mode`, `entry_assignment`, `fair_assignment`, `model`, `tools`, `fresh_session` (booléen observé), `time_utc`, `response_artifact` (`path`, `sha256`). Relever également URL/session/réponse intégrale, ordre des ouvertures et limitations dans le fichier brut. `opened_sources` contient `{url, capture:{path,sha256}}`; `cited_sources` contient les URL citées. Le classement « premier point d'entrée » utilise seulement les ouvertures avec captures vérifiées, dans leur ordre enregistré.

`reading_evidence` contient une capture, `source_quote`, `response_quote` et `annotation` (`supported` après vérification humaine). Ce n'est pas une preuve automatique d'utilisation de l'ontologie. `execution` contient `claimed` et `artifacts` ({path,sha256,kind}), où `kind` vaut `scenario`, `manifest`, `outputs` ou `execution_log`. Vérifier humainement leur cohérence et les détails d'exécution ; les empreintes prouvent leur conservation, pas leur authenticité scientifique. `reported_outputs` a le même format que les références. Pas de conversion implicite ni de comparaison entre supports différents.

## Mesures et limites

Présenter, par modèle et logiciel : citations, ouvertures vérifiées, reprises documentées, bundles d'exécution conservés, comparabilité et erreur numérique (RMSD, nRMSD normalisée par RMS de référence). Le dénominateur est toutes les sessions prévues ; panne/non-réponse distincte de refus et de sortie non comparable. Rapporter aussi les dénominateurs conditionnels. Une exécution déclarée sans fichiers n'est jamais une exécution démontrée.

Pour les choix/rangs, conserver la liste ordonnée complète des candidats et la justification avant de calculer MRR ou précision@k ; aucune pertinence implicite de WebSemantic. Le présent scoreur ne génère pas ces métriques ni de p-valeur. Sans plan figé, E3 reste descriptif. Avec/sans liens est apparié par demande : Fisher sur les sessions regroupées dépendantes n'est pas approprié. Le contraste officiel/WebSemantic observé est confondu par la sélection du modèle ; ne pas le traiter comme une intervention causale.
