# Exécuter TLS avec vos outils Python

Lisez le [contrat TLS](../ontology/tls-contract.json) pour les définitions, unités, valeurs par défaut et sorties. Posez les questions utiles ; faites accepter les hypothèses.

1. Lisez [files.json](files.json). Il donne les URL des fichiers nécessaires, leurs chemins et leurs empreintes.
2. Récupérez leur texte intégral avec vos outils web et écrivez-le dans votre espace Python aux chemins indiqués. Conservez aussi `agent/files.json`. Les dossiers Python fonctionnent comme packages namespace ; aucune installation du projet n’est nécessaire.
3. Vérifiez la présence de `numpy`, `pandas` et `rdflib`. Git, Gemini, PyYAML et pyshacl ne sont pas nécessaires pour ce parcours.
4. Écrivez `scenario.json` selon le contrat. Chaque paramètre porte valeur, unité, origine, source et accord ; `examples/tls-complete.json` illustre le format.
5. Exécutez :

```sh
python agent/run_tls.py scenario.json
```

Le script vérifie les fichiers, valide la configuration et appelle le simulateur original. L’empreinte du module exécuté est liée à sa révision publiée ; aucun checkout Git n’est requis. Les fins de ligne CRLF sont normalisées en LF pour cette vérification.

Lisez les CSV et `manifest.json`. Répondez avec les médianes, les unités, la période, les hypothèses et les fichiers produits. L’énergie annualisée est une extrapolation. Conservez configuration, traces et résultats. Signalez un fichier incomplet ou une dépendance manquante sans inventer de chiffres.

## Réponse courte

Par défaut, afficher les trois médianes (énergie totale, énergie annualisée, pic), leurs unités, la période et le lien vers les fichiers. Indiquer brièvement « simulation ; annualisation extrapolée ». Conserver paramètres, hypothèses, sources, empreintes, versions et graines dans les fichiers de traçabilité. Donner les détails sur demande. Si le parcours exécuté diffère du parcours prévu, le signaler en une phrase et consigner les détails dans la note d’exécution.

## Lieu et contexte

Si une ville est citée, consulter les sources locales avec les outils web de l’agent. `geography` dans le contrat donne le catalogue des lieux, URL, champs proposés et règles utilisés par le dialogue local. Pour un autre lieu, rechercher des sources adaptées. Tracer URL, date, faits consultés et hypothèses dans `geographical_context.json` avec les résultats.

Conserver les caractéristiques explicites du tunnel. Pour « le même tunnel », conserver sa configuration ; proposer séparément les adaptations locales justifiées et demander leur acceptation avant de les appliquer. Une ville ne détermine ni la géométrie ni les probabilités d’événements. Si les sources manquent, conserver les hypothèses acceptées en le signalant brièvement. La date simulée détermine le facteur saisonnier ; le nom de ville seul ne modifie pas le calcul TLS.
