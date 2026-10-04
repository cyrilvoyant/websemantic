# WebSemantic

WebSemantic permet de préparer un scénario en langage naturel, de vérifier ses hypothèses et d’exécuter un logiciel scientifique dans une version fixée. Les résultats sont accompagnés de leurs unités, de la configuration utilisée et de leurs limites d’interprétation.

La version actuelle concerne TLS, un modèle de demande électrique des tunnels routiers. LQL-Equiv et pvlib sont proposés au menu, mais leur intégration conversationnelle reste en préparation. Les données produites par TLS sont synthétiques ; aucune validation sur des mesures de terrain n’est revendiquée.

## Utilisation

Avec le package Windows de validation, décompressez l’archive puis ouvrez `Installer.cmd` une fois. Pour les utilisations suivantes, ouvrez `WebSemantic.cmd` et choisissez TLS. Le lanceur vérifie l’installation et indique si une réparation est nécessaire.

Décrivez votre étude, puis précisez progressivement vos choix. Par exemple :

> Je voudrais étudier un tunnel de 2 km, avec deux tubes, un éclairage LED fixe et une ventilation longitudinale. Propose les informations manquantes sans les accepter.

Vous pouvez demander un tableau avec unités, une définition, des sources ou cinq pistes d’affinement. Les hypothèses scientifiques restent à accepter explicitement. Le calcul démarre quand la configuration est complète et admissible ; une modification explicite permet un nouveau calcul. Les questions de consultation ne relancent pas une simulation.

Le dialogue présente les choix principaux. Le détail complet reste accessible sur demande. La graine technique est fixée à 42, sauf modification explicite ; elle est conservée dans les fichiers de résultats.

Le module conversationnel utilise Gemini. Le clone public ne contient aucune clé ; la configuration est décrite dans [l’installation Windows](docs/installation-windows.md). Les archives privées de validation ne doivent pas être publiées.

## Installer depuis le dépôt

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls]"
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

Sous Linux ou macOS, utilisez `.venv/bin/python`. Voir [l’utilisation du terminal](docs/terminal.md) pour les raccourcis et les réglages.

## Paramètres et résultats

Le [référentiel TLS](docs/tls-reference.md) décrit les 26 paramètres : sens, unité, type, catégories, bornes, rôle dans le modèle et précautions d’emploi. Les valeurs fournies, les conversions et les hypothèses acceptées restent distinctes. Les valeurs manquantes ne sont pas remplacées silencieusement par des hypothèses physiques.

Chaque calcul écrit un dossier contenant :

| Fichier | Contenu |
|---|---|
| `kpis.csv` | Indicateurs par réalisation, graine de base et graine utilisée |
| `representative.csv` | Trajectoire native de la réalisation 0 |
| `daily.csv` | Énergie et puissance moyenne par jour, réalisation 0 |
| `envelope.csv` | Statistiques horaires entre réalisations |
| `season_profiles.csv` | Profils des saisons effectivement simulées |
| `manifest.json` | Configuration, sources, acceptations, révision TLS et qualification des sorties |
| `semantics.ttl` | Définitions et provenance en RDF |

L’énergie totale couvre la période simulée. L’énergie annualisée applique `365/n_days` ; elle ne devient pas une mesure annuelle. La puissance est exprimée en kW et l’énergie en kWh ou MWh selon la table. L’énergie spécifique est en kWh/(m·an), tous tubes compris. Les quantiles Monte Carlo ne sont pas des intervalles de confiance sur une consommation réelle.

## Contrat sémantique

Les définitions sont maintenues dans le [descripteur TLS](descriptors/tls/descriptor.yaml), puis publiées sous trois formes : [contrat JSON](ontology/tls-contract.json), [schéma de scénario](ontology/tls-scenario.schema.json) et [vocabulaire RDF/SKOS](ontology/tls-vocabulary.ttl). L’ontologie distingue paramètres, hypothèses, réglages techniques, scénarios, exécutions et sorties.

Les contrôles Python et l’adaptateur font autorité avant le calcul. Le graphe apporte les relations et la provenance ; il n’exécute pas un contrôle SHACL ni un raisonnement OWL. L’alignement QUDT et les exports JSON-LD restent à développer.

Pour un accès programmatique ou l’essai avec un agent externe, consulter le [contrat d’exécution](docs/agent-contract.md). L’essai demande à l’agent de lire le dépôt, de préparer son script Python et d’exécuter réellement TLS ; aucun résultat précalculé ne remplace cette étape. Il faut un service avec exécution Python activée ou un agent local ayant accès à Python, au dépôt et à l’installation des dépendances ; une conversation seule ne suffit pas.

## Validation et développement

Les sources des simulateurs et leurs déploiements restent inchangés. TLS est fixé au commit `748e053e129669cf3e896d381e3c0ac01c763edd`. L’adaptateur refuse une autre révision ou des modifications suivies du backend. Les tests de logiciel, la comparaison entre interfaces et la validation physique sont trois niveaux distincts.

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[dev,tls]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m ruff check .
```

Le [protocole](docs/protocol.md) précise les comparaisons prévues, les graines et les métriques. Aucun résultat comparatif ni transfert scientifique LQL/pvlib n’est encore établi. L’ajout d’un logiciel suit le [contrat d’intégration](docs/integrating-models.md).

## Citation et licence

Cyril Voyant, Haytham El-Houari, Daniel Julian et Nicolas Fichaux. Les informations de citation sont dans [CITATION.cff](CITATION.cff).

Le code WebSemantic courant est sous [PolyForm Noncommercial 1.0.0](LICENSE). Les simulateurs et dépendances conservent leurs licences. Les révisions antérieures publiées sous MIT jusqu’au commit `c00914c` conservent ces permissions. Cette licence comporte des restrictions commerciales et n’est pas une licence open source au sens de l’OSI.

Les formulations « beaucoup de trafic » et « énormément de trafic » proposent respectivement 1,5 et 2, sans unité : 75 % et 100 % de la référence haute du curseur TLS. Cette convention est déclarée dans le contrat et contrôlée localement. Les propositions restent à valider ; elles ne représentent pas des comptages de véhicules.

Chaque variable possède une règle d’interprétation : 21 échelles de scénario pour les quantités et 5 politiques pour les catégories, la date et la graine. Les expressions, valeurs, unités et références figurent dans [le référentiel](docs/tls-reference.md). Les qualificatifs inconnus ou ambigus demandent une précision ; une valeur explicite reste prioritaire.

Le dialogue pose une ou deux questions ciblées en cas de doute. Une ambiguïté bloquante reste ouverte jusqu’à une réponse portant sur le choix concerné ; consulter le tableau ou accepter globalement les hypothèses ne la résout pas. Demandez « le tableau des défauts et des valeurs retenues » ou « les formules utilisées » pour examiner le scénario. Les faits documentés restent distincts des hypothèses locales de trafic, pollution ou accidents.

Deux scénarios peuvent être comparés dans une même conversation. Précisez les valeurs communes et les différences ; chaque configuration conserve ses hypothèses et sa validation. Les deux calculs partagent le calendrier, le pas, le nombre de réalisations et la graine. Les CSV réunis ajoutent `scenario` (`scenario_1`, `scenario_2`) ; les sorties individuelles restent dans leurs sous-dossiers. `comparison.json` donne les différences entre médianes, sans moyenne entre scénarios. Le guide fournit cet essai en exemple 3 ; l’essai avec un agent externe devient l’exemple 4.
