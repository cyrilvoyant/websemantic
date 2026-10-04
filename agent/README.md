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
