# WebSemantic

Préparer une simulation TLS en phrases, examiner les hypothèses et obtenir des résultats avec leurs unités et leur provenance.

## Utiliser

Dans le package Windows, ouvrez `Installer.cmd` une fois, puis `WebSemantic.cmd` et choisissez TLS.

> Étudie un tunnel fictif de 2 km, deux tubes et deux voies par tube, avec éclairage LED fixe et ventilation longitudinale. Propose les paramètres manquants.

Demandez le tableau des paramètres ou les formules, précisez les choix, puis acceptez les hypothèses. Le calcul démarre lorsque la configuration est complète et validée. Une modification explicite recalcule l’étude. Le dossier des résultats est affiché à chaque calcul.

Le [guide](packaging/windows/Guide.txt) propose quatre essais, dont une comparaison de deux tunnels et une exécution par un agent Python.

## Installer depuis GitHub

Python 3.10+ et Git sont nécessaires. Configurez `GEMINI_API_KEY` pour le dialogue.

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls]"
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

[Installation](docs/installation-windows.md) · [Dialogue et raccourcis](docs/terminal.md)

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

[PolyForm Noncommercial 1.0.0](LICENSE). Les composants conservent leurs licences ; les révisions déjà publiées sous MIT conservent leurs permissions. Le dépôt public ne contient aucune clé. Les archives privées de validation restent privées.
