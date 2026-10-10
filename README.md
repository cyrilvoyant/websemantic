# WebSemantic

Préparer une simulation en phrases, examiner les hypothèses et obtenir des résultats avec leurs unités et leur provenance. Trois profils : TLS, LQL-Equiv (un cursus fictif) et pyrcel (un mode d’aérosol, ascendance constante).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23238902.svg)](https://doi.org/10.5281/zenodo.23238902) [![PyPI](https://img.shields.io/pypi/v/websemantic.svg)](https://pypi.org/project/websemantic/) [![OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/projects/15359/badge)](https://www.bestpractices.dev/projects/15359) · ontologie : [w3id.org/websemantic/ns](https://w3id.org/websemantic/ns) · [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md)

## Avec un agent Python

Lisez [les règles de réutilisation](llm.md), puis [le point d’entrée Python](agent/README.md). Il indique les fichiers, leurs empreintes et la commande commune aux trois modèles : `python agent/run.py tls|lql|pyrcel scenario.json` (choisir un modèle). Ce parcours utilise les fichiers sources, sans Git ni clé Gemini.

## Utiliser

Dans le package Windows, ouvrez `Installer.cmd` une fois, puis `WebSemantic.cmd` et choisissez 1 (TLS), 2 (LQL) ou 3 (pyrcel).

> Étudie un tunnel fictif de 2 km, deux tubes et deux voies par tube, avec éclairage LED fixe et ventilation longitudinale. Propose les paramètres manquants.

Demandez le tableau des paramètres ou les formules, précisez les choix, puis acceptez les hypothèses. Le calcul démarre lorsque la configuration est complète et validée. Une modification explicite recalcule l’étude. Le dossier des résultats est affiché à chaque calcul.

Le [guide](packaging/windows/Guide.txt) propose quatre essais, dont une comparaison de deux tunnels et une exécution par un agent Python.

## Installer depuis GitHub

Python 3.12+ et Git sont nécessaires pour installer les trois profils depuis GitHub. Configurez `GEMINI_API_KEY` pour le dialogue.

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls,atmosphere]"
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

[Installation](docs/installation-windows.md) · [Dialogue et raccourcis](docs/terminal.md)

## Autres profils

LQL : « Étudie un schéma fictif rectum/prostate : 20 fractions de 3 Gy, référence 2 Gy. Propose les hypothèses manquantes. »

pyrcel : « Simule une parcelle à 1 m/s, 283 K, 850 hPa et S0 = -0,02 ; un mode lognormal de 1000 particules/cm³, rayon sec médian 0,05 µm, sigma 2, kappa 0,54. Propose les réglages manquants. »

Examinez les paramètres et leurs unités, puis acceptez les hypothèses. LQL sert à la recherche sur des schémas fictifs ; pyrcel simule une parcelle idéale.

## Résultats

TLS produit des données simulées. L’énergie totale couvre la période calculée ; l’énergie annualisée extrapole par `365/n_days`. Puissance : kW ; énergie : kWh ou MWh selon la table.

Les CSV contiennent les trajectoires, les séries journalières, les profils et les indicateurs par réalisation. `manifest.json` décrit les paramètres, les sources, les unités et les agrégations ; `semantics.ttl` conserve la provenance. Une comparaison ajoute `scenario` aux CSV réunis et conserve les deux calculs individuels. `comparison.json` donne les écarts entre médianes.

[Paramètres et sorties TLS](docs/tls-reference.md) · [Contrat JSON](ontology/tls-contract.json) · [Exécution depuis un agent](docs/agent-contract.md)

## Développement

Les définitions sont maintenues dans le [descripteur](descriptors/tls/descriptor.yaml). Le calcul utilise l’adaptateur et le backend TLS fixé, sans modifier ses sources.

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[dev,tls]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m ruff check src tests tools
```

[Architecture](docs/architecture.md) · [Intégration](docs/integrating-models.md) · [Protocole](docs/protocol.md)

## Licence

[MIT](LICENSE), depuis la version 0.2.6 ; les versions 0.2.0 à 0.2.5 restent sous PolyForm Noncommercial 1.0.0. Les composants conservent leurs licences (TLS et LQL-Equiv : MIT ; pyrcel : BSD-3-Clause). Le dépôt public ne contient aucune clé. Les archives privées de validation restent privées.
