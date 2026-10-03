# websemantic

**A software-agnostic semantic layer between human intent and existing scientific simulators.**

> Status: early terminal proof of concept (October 2026). Gemini interpretation, deterministic validation, explicit demonstration-profile acceptance and pinned local TLS execution are implemented. CSV outputs and an initial JSON manifest are saved. An initial RDF/SKOS vocabulary and PROV-O export are implemented. No comparative benchmark, transfer study, JSON-LD or SHACL execution gate yet.

## Try the terminal PoC

**Windows :** décompressez entièrement le package privé, puis double-cliquez sur `Installer.cmd`. Pour les usages suivants, ouvrez `WebSemantic_TLS.cmd` : ce lanceur ne réalise aucune installation. Le menu propose TLS (disponible), LQL et pvlib (Work in progress). Les composants compatibles déjà présents sont conservés. Le `.env` du package privé est lu automatiquement ; le clone GitHub ne contient aucune clé. Ne lancez pas directement depuis le ZIP et ne publiez pas l’archive privée.

**Installation on another Windows PC:** [French step-by-step guide](docs/installation-windows.md). Clone with submodules, install `.[tls]`, configure your own Gemini key, then run the terminal. No activation or GUI is required.

See [PowerShell instructions](docs/terminal.md). On the configured local machine:

```powershell
cd C:\Users\cvoyant\Documents\websemantic\semantic-sim-layer
& .\.venv\Scripts\websemantic.exe chat --model tls
```

Write a request, inspect `/show`, then optionally `/profile`, `/accept` and `/run`. No local conversation ceiling by default; Gemini project quotas still apply. No automatic retry. Original backend sources stay unchanged. API credentials are read locally from GEMINI_API_KEY or a private .env file, never versioned.


## Purpose

Scientific software exposes numerical parameters, while users ask questions. This repository studies a generic, non-intrusive layer that:

1. turns a natural-language request into a **traceable semantic state**: every value is user-provided, deterministically transformed, an accepted assumption or unknown, and none is silently invented;
2. **selects** a suitable model and validates a configuration before any run, by checking structure, units, bounds, completeness, conflicts and task suitability;
3. runs the **unmodified** simulator;
4. **qualifies the simulated data**: each output is published as a self-describing JSON-LD record stating which software, version and configuration produced it, which assumptions were accepted, which uncertainties are and are not covered, and what uses are admitted or excluded.

The architectural goal is a shared core with software-specific **descriptors** and **adapters**. Transfer without core changes is a hypothesis to test after a core freeze, not an established guarantee for arbitrary software.

## First implemented slice

`src/websemantic/core/validation.py` defines parameter records, scenarios and structured issue reports. `validate(scenario, descriptor)` returns `execute`, `clarify` or `refuse` without completing or changing the scenario. It checks missing values, conflicting candidates, exact evidence-span presence, sourced and explicitly accepted assumptions, strict numeric types (excluding booleans), finite values, canonical units, categories, dates and declared bounds. Experiment positivity and non-negative seed bounds are explicit prototype policies in the TLS descriptor.

Limitations: exact declared-task matching only; evidence presence is not semantic proof; no SHACL or general unit conversion. The terminal normalizes quoted lengths, applies TLS resource limits and runs the pinned backend. It supports one scenario at a time; comparisons request clarification. `execute` means this initial gate has no reported issue, not certification of the experiment. This is a research prototype.

The local development environment is `.venv/`; `requirements-tested.txt` records installed versions used for verification. Install the project separately with `pip install -e .` when recreating that environment. Tests: `python -m pytest -q`. The refactored implementation is checked by the automated regression suite, including independent descriptor-only structural fixtures and the existing backend smoke tests. These are software checks, not benchmark evidence of scientific benefit.

## Design principles

- **Non-intrusive**: target software is never modified, locally or on GitHub. TLS and LQL-Equiv are linked as git submodules pinned to exact commits (read-only references); pvlib is a pinned PyPI dependency. Only their public APIs are called.
- **Non-invention**: an unsupported value that is not an accepted assumption cannot reach the simulator.
- **LLM as interpreter, not as calculator**: the language model only sees deterministic tools generated from descriptors (`describe_model`, `propose_config`, `validate`, `run`, `annotate`). It never executes code and never computes results. Any explanation reads annotated outputs only.
- **Model comparisons planned**: Gemini is implemented; Claude/GPT repository-reading baselines and within-model comparisons remain prospective. Ranking models alone is not the research objective.
- **Standards**: QUDT for units, PROV-O for provenance, SHACL for the execution gate, DCAT and schema.org for output datasets, CodeMeta and CITATION.cff as input to model selection.

## Case studies

| Role | Software | Domain | Link | Licence |
|---|---|---|---|---|
| Development case (core built here, then frozen) | Tunnel Load Simulator (TLS) | Road-tunnel electricity demand, Monte Carlo | submodule `external/tunnel-load-simulator` @ `748e053` · [repo](https://github.com/cyrilvoyant/tunnel-load-simulator) · [DOI](https://doi.org/10.5281/zenodo.20080042) | MIT |
| Held-out case 1 (same authors, other domain) | LQL-Equiv | Radiobiology: BED, EQD2, NTCP, TCP | submodule `external/LQL-Equiv-web` @ `dfc9a33` · [repo](https://github.com/cyrilvoyant/LQL-Equiv-web) · [DOI](https://doi.org/10.5281/zenodo.21948623) | MIT |
| Held-out case 2 (third-party library) | pvlib-python | PV system modelling | PyPI `pvlib==0.16.1` · [repo](https://github.com/pvlib/pvlib-python) | BSD-3-Clause |

**Genericity protocol**: the core is developed on TLS only, then frozen with the git tag `core-frozen`. LQL-Equiv and pvlib are then integrated by adding descriptors and adapters only. Any required change to the core is logged and reported as a partial genericity failure. Integration cost is measured: descriptor and adapter lines, time, and fields auto-filled versus written by hand.

**Scope limits**:
- LQL-Equiv is research and education software, not a medical device. Individual-patient clinical requests are an *expected refusal* class.
- pvlib is restricted to declared task profiles (e.g. `ModelChain`). Requests outside a profile are refused or flagged, never improvised.
- No measured tunnel, PV or clinical data are used. Simulator outputs are computational references, not observations.

**DOI policy**: software is cited by its concept DOI (all versions) and pinned by commit, because the pinned commits postdate the archived releases. TLS: concept `10.5281/zenodo.20080042` (v1.0.1: `20080043`). LQL-Equiv: concept `10.5281/zenodo.21948623` (v3.0.0: `21948624`).

## Repository layout

```
src/websemantic/core/      generic core: semantic state, parser, clarification, validation, selection, run, annotation
src/websemantic/adapters/  thin per-software adapters (the only code touching target APIs)
descriptors/{tls,lqlequiv,pvlib}/ declarative descriptors (inputs, outputs, tasks, validity, entry point)
ontology/                         initial RDF/SKOS vocabulary (OWL/SHACL/JSON-LD planned)
benchmark/                        requests, reference annotations, evaluation scripts
docs/                             architecture, protocol, decisions, context
external/                         pinned submodules (read-only, never edited)
tests/                            smoke and non-regression tests
```

## Getting started

```bash
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,backends]"
pytest
```

The smoke test checks that TLS and LQL-Equiv still run through the submodules and reproduce a documented reference output.

## Documentation

- [docs/architecture.md](docs/architecture.md): components and data flow
- [docs/protocol.md](docs/protocol.md): benchmark, comparators, metrics
- [docs/decisions.md](docs/decisions.md): decision log
- [docs/context.md](docs/context.md): origin of the study and the remarks from the 2 October 2026 demonstration

Project governance (Cyril / Codex / Claude) is kept in `trilog.md` in the parent working folder, outside this repository.

## Authors and citation

- Cyril Voyant, Mines Paris – PSL, O.I.E. ([ORCID 0000-0003-0242-7377](https://orcid.org/0000-0003-0242-7377))
- Haytham El-Houari, Université Sidi Mohamed Ben Abdellah (USMBA), Fès, Morocco (co-author of TLS)
- Daniel Julian, Centre de Cancérologie du Grand Montpellier (co-author of LQL-Equiv)
- Nicolas Fichaux (origin of the user-intent demonstration, see [docs/context.md](docs/context.md))

See [CITATION.cff](CITATION.cff).

Homepage: <https://www.cyrilvoyant.com>

## Licence

PolyForm Noncommercial 1.0.0 for the current code authored for this repository, with the attribution notices in LICENSE to retain on redistribution. Commercial uses outside the licence’s permitted purposes require a separate authorization from the rights holder. This is source-available software with noncommercial restrictions, not an OSI-approved open-source licence. Linked and dependent software keep their own licences (TLS: MIT; LQL-Equiv: MIT; pvlib: BSD-3-Clause). Earlier revisions published under MIT, through commit c00914c, retain their MIT permissions; this change does not revoke rights already granted. See the full LICENSE text for the permitted purposes, including its provisions for educational/public research organizations.

## Essais en langage naturel

Ces essais permettent de vérifier l'interprétation, les unités et les demandes de précision. Ouvrir une nouvelle session pour chaque essai indépendant. Une demande de calcul démarre dès que les paramètres sont complets et les hypothèses validées. Une demande incomplète reste en attente ; les explications ne déclenchent aucun calcul.

| Phrase à saisir | Comportement attendu |
|---|---|
| Je souhaite estimer la consommation électrique d'un tunnel de 2 km, avec deux tubes et deux voies par tube, en contexte périurbain. | Extraire les paramètres et convertir la longueur en 2 000 m. Demander les informations manquantes. |
| Le tunnel mesure 1 500 mètres et possède un seul tube avec deux voies. | Reconnaître les unités et les nombres écrits en lettres. |
| Le tunnel utilise un éclairage LED fixe et une ventilation longitudinale. | Reconnaître les catégories déclarées du simulateur. |
| Simule 30 jours à partir du 1er janvier 2025, avec un pas de 15 minutes et 10 réalisations. | Extraire la date, la durée, le pas temporel et le nombre de réalisations. |
| Je veux connaître la consommation d'un tunnel. | Demander des précisions sans inventer les paramètres. |
| Le trafic est très élevé. | Ne pas convertir cette description en multiplicateur numérique arbitraire. |
| Le tunnel mesure moins de deux kilomètres. | Demander une longueur précise ; ne pas transformer une borne en valeur exacte. |
| Le tunnel possède zéro tube. | Extraire la valeur, puis bloquer le calcul à la validation. |
| Compare un tunnel de 1 km fortement éclairé et un tunnel de 2 km faiblement éclairé. | Demander de séparer les scénarios ; expliquer que l'intensité fort/faible n'est pas paramétrée dans ce PoC. |
| Donne-moi la consommation réelle exacte de ce tunnel pour l'année prochaine. | Refuser cette prédiction réelle sans calibration. |

Il s'agit de comportements à vérifier, pas de résultats garantis : certains essais peuvent révéler une erreur d'interprétation ou une limite de la validation. Conserver la phrase exacte et la réponse obtenue pour le retour de test.

### Corriger une valeur en cours de conversation

Saisir successivement dans la même session :

```text
Le tunnel mesure 2 km, avec deux tubes et deux voies par tube.
Correction : sa longueur est de 1,5 km.
/show
/details
```

La longueur finale attendue est 1 500 m. Les nombres de tubes et de voies doivent rester inchangés.

### Aller jusqu'aux résultats

```text
Je souhaite estimer la consommation d'un tunnel de 2 km.
/profile
/details
/accept
/run
```

Lire les hypothèses proposées avant `/accept`. Ce profil est un exemple de calcul, pas une description mesurée du tunnel.

Vérifier que la réponse distingue l'énergie sur la période (MWh), l'énergie annualisée par extrapolation (MWh/an), la puissance de pointe au pas de calcul (kW), l'énergie annualisée par longueur tous tubes compris (kWh/(m·an)) et le facteur de charge sans dimension. Dans `manifest.json`, `output_qualification` décrit les unités, le sens des colonnes et les agrégations. Les quantiles p10–p90 caractérisent les réalisations simulées ; ils ne constituent pas un intervalle de confiance.

Par défaut, la conversation ne comporte plus de plafond local ; les quotas Gemini restent applicables. Les commandes `/show`, `/details`, `/profile`, `/accept` et `/run` ne consomment pas d'appel API.

Le lanceur vérifie Git, Python, les dépendances et le commit TLS. Il installe les outils absents via winget, puis les dépendances Python. Une connexion Internet est nécessaire ; Windows peut demander une autorisation administrateur. Si winget est absent, installer App Installer depuis le Microsoft Store puis relancer. Les branches d'installation des outils absents restent à tester sur un PC vierge. Documentation winget : https://learn.microsoft.com/en-us/windows/package-manager/winget/install

## Mise à jour du test conversationnel

Les commandes courtes sont rappelées après chaque échange : `/d` tableau des valeurs et unités, `/e altitude_m` définition d'une variable, `/p` proposition, `/v` validation des hypothèses, `/r` calcul, `/q` sortie. Les mêmes alias avec antislash sont acceptés. Les commandes copiées avec une explication après leur nom sont reconnues.

« Prends les valeurs moyennes » accepte explicitement les valeurs de démonstration pour les champs manquants ; ce ne sont pas des moyennes terrain. « Comme Ajaccio » propose un contexte documenté à valider, sans inventer les paramètres d'un tunnel réel. « Les plus coûteux énergétiquement » propose les catégories à coefficients élevés dans TLS, sans prétendre à un optimum.

La conversation n'a plus de plafond local par défaut (`--max-calls 0`) ; les quotas Gemini demeurent. Le nombre de réalisations n'est plus limité à 30 ; un garde de volume de deux millions de points reste actif. Résultats en tableau français (moyenne et médiane), export JSON et RDF. Dans le package, le dossier `Resultats` apparaît à côté du lanceur et s'ouvre à la fin du calcul. Une installation depuis un partage réseau utilise AppData uniquement pour l'environnement technique.

Pour une étude plus détaillée, utiliser le simulateur TLS original : https://github.com/cyrilvoyant/tunnel-load-simulator . Le lien direct de l'interface déployée reste à confirmer ; aucun domaine .net n'est deviné.

Pour affiner l'objectif : taper /s ou \s. Cinq choix sont proposés selon les paramètres manquants, le contexte Ajaccio et la présence de résultats. Saisir 1 à 5 ou écrire une autre question. Les suggestions n'acceptent aucune hypothèse ; les choix d'objectif peuvent demander un calcul soumis aux contrôles ; une question d'objectif sélectionnée peut utiliser Gemini, les explications de paramètres sont locales.

## Calcul à la demande
« Calcule » ou « estime la consommation » suffit : le calcul démarre quand les informations passent les contrôles. Si elles manquent, la demande reste en attente et repart après complément ou validation des hypothèses. /run et /r sont facultatifs. « Annule le calcul » annule une demande en attente. Les explications, tableaux et suggestions ne relancent pas un calcul terminé.

### Contexte géographique documentaire

« Comme Paris » ou « comme Ajaccio » déclenche maintenant une consultation directe de sources publiques sélectionnées, puis une analyse Gemini structurée. Le terminal montre les quatre thèmes trafic, pollution, accidents et pics horaires, un tableau avec unités et statut, ainsi que les URLs et dates de consultation. Deux appels Gemini sont utilisés : extraction des valeurs explicites, puis interprétation des sources. Les étapes techniques ne sont pas affichées.

Les propositions restent des hypothèses à valider avec `/v`, et les valeurs explicitement saisies restent prioritaires. Une demande de calcul antérieure démarre après validation. Aucun comptage local n’est extrait à ce stade : en son absence, les pics 8 h/18 h, largeur 1,4 h et trafic relatif 1 restent des défauts non calibrés. Les données d’air ambiant et BAAC ne déterminent pas automatiquement les probabilités d’événements TLS. La géométrie et l’altitude du tunnel ne sont pas déduites de la commune.

Le module couvre pour l’instant Paris et Ajaccio. Il consulte un catalogue limité de pages, sans recherche ouverte Google : les essais de grounding Gemini avec cette clé n’ont pas abouti (HTTP 429/404). Les sources inaccessibles sont signalées ; un échec d’analyse bloque le calcul demandé, y compris sur un ancien scénario valide. `geographic-context.json` conserve le contexte et les références dans chaque dossier de résultats. Les rapports historiques ne sont pas présentés comme des mesures actuelles.

Exemple : `Calcule un tunnel de 1500 m comme Ajaccio avec des hypothèses de trafic, pollution, accidents et pics matin et soir`, puis `/v`.

### Lancement sans installation

`WebSemantic_TLS.cmd` effectue uniquement des contrôles avant d’ouvrir la conversation : environnement Python, versions minimales des dépendances, imports et révision TLS. Si quelque chose manque, il indique de lancer `Installer.cmd` ; aucun installateur n’est appelé par le lanceur.

`Installer.cmd` vérifie l’environnement réel, sans se baser sur un fichier témoin. Python >=3.10 et les bibliothèques plus récentes compatibles sont conservés. `pip install -e .[tls]` n’est exécuté que si une dépendance manque, est trop ancienne ou ne se charge pas ; sans option `--upgrade` ni réinstallation forcée. L’installateur n’ouvre jamais la conversation. Le backend TLS reste fixé au commit scientifique déclaré, indépendamment des versions des outils d’installation.

### Recherche web au-delà de la géographie

La recherche documentaire est autorisée pour les questions techniques et scientifiques : éclairage, ventilation, unités, méthodes, références ou données externes. Écrivez « Recherche sur le web… » ou `/web QUESTION`. Gemini peut aussi demander automatiquement une recherche si la question nécessite des sources externes. Les définitions déjà présentes et les commandes restent locales.

Le module utilise la recherche publique Bing RSS sans clé supplémentaire, consulte jusqu’à quatre pages et demande à Gemini une synthèse courte en français, avec unités, références et limites. Les pages non accessibles ou non textuelles sont signalées ; un document PDF lié n’est pas assimilé à un document lu. Les étapes internes ne sont pas affichées. Le service de recherche public peut devenir indisponible ; aucun résultat n’est inventé en cas d’échec.

Une réponse documentaire ne modifie et ne valide aucun paramètre et ne déclenche aucun calcul. Elle est conservée dans l’historique et immédiatement dans `documentation.jsonl` sous le dossier des résultats, même sans calcul ; `web-context.json` est enregistré avec les prochains résultats de simulation. Les sources peuvent expliquer un choix, mais les valeurs de simulation restent soumises au descripteur et à la validation. Les pages web sont des données, jamais des instructions exécutables.

Exemple : `/web CETU rôle de la ventilation et de l’éclairage dans la consommation électrique d’un tunnel`.

### Choix de l’environnement au démarrage

Le lanceur interactif affiche les environnements et leur domaine avant la conversation :

| Choix | Environnement | Domaine | État |
| --- | --- | --- | --- |
| 1 | `websemantic.tls` | Demande électrique des tunnels routiers | Disponible |
| 2 | `websemantic.lql` | Équivalences radiobiologiques | Work in progress |
| 3 | `websemantic.pvlib` | Systèmes photovoltaïques | Work in progress |

Saisir 2 ou 3 affiche « Work in progress » puis réaffiche le menu, sans chargement de ces backends ni requête LLM. Saisir 1 ouvre le prompt `websemantic.tls >`. `q` quitte le menu. Ces noms identifient les environnements ; les adaptateurs conversationnels LQL/pvlib restent à implémenter. Le menu ne constitue pas une validation de transfert entre logiciels.

`websemantic chat` affiche ce menu. `websemantic chat --direct --model tls` permet un démarrage TLS direct pour les scripts et les tests. `--once` conserve une exécution non interactive ; demander un modèle indisponible avec `--once` retourne Work in progress et un code d’échec, sans basculer silencieusement sur TLS. L’environnement TLS est aussi enregistré dans `conversation.json` avec les résultats.

Le menu est aussi affiché par les anciens lanceurs qui préselectionnaient TLS : le démarrage interactif reste un choix utilisateur. Seul `--direct` désactive explicitement le menu.

## Descriptor-driven integration

TLS labels, defaults, geographical catalogue, qualitative rules, extraction guidance and result presentation are now declared in its descriptor. The session, validation, RDF export and CLI dispatch are shared. Numerical backend constraints and output qualification remain in the TLS adapter. See [the integration contract](docs/integrating-models.md). LQL and pvlib are still placeholders; structural fixtures do not establish scientific transfer performance.
