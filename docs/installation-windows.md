# Tester WebSemantic_TLS sur un autre PC Windows

Prototype de recherche : terminal PowerShell, Gemini pour interpréter les demandes et TLS pour calculer localement. Aucune interface graphique. Les sources TLS sont des références Git figées et ne sont pas modifiées.

## 1. Installer le code

Prérequis : Git et Python 3.10 ou supérieur, accessibles avec `git --version` et `py --version`. Python 3.12 est conseillé pour reproduire l'environnement de développement.

Dans PowerShell, depuis le dossier où vous souhaitez installer le prototype :

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e '.[tls]'
& .\.venv\Scripts\websemantic.exe models
```

Si une autre version compatible est installée, remplacer `py -3.12` par `py`. L'activation du venv n'est pas nécessaire. Utiliser le clone Git, car le ZIP GitHub n'inclut pas le contenu des sous-modules.

Pour un clone existant : `git submodule update --init --recursive`.

## 2. Configurer sa propre clé Gemini

Créer une clé dans Google AI Studio. Chaque testeur utilise sa propre clé et son propre quota. Ne pas envoyer la clé à Cyril ni la déposer sur GitHub.

Dans le même PowerShell, saisir la clé de façon masquée :

```powershell
$geminiSecret = Read-Host 'Votre clé Gemini (saisie masquée)' -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $geminiSecret).Password
Remove-Variable geminiSecret
```

Cette configuration dure uniquement pendant la session PowerShell. Le programme peut aussi lire la variable utilisateur Windows `GEMINI_API_KEY`. Ne pas saisir la clé dans la conversation.

Le modèle par défaut est `gemini-3.5-flash-lite`, utilisé lors des essais de développement. Son accès dépend du compte ; un modèle autorisé peut être choisi avec `--llm NOM_DU_MODELE`. Les limites et la facturation sont celles du projet Google du testeur.

## 3. Converser et lancer un calcul

```powershell
& .\.venv\Scripts\websemantic.exe chat --model tls --max-calls 5
```

Exemple à saisir après `WebSemantic_TLS >` :

```text
Je souhaite estimer la consommation électrique d'un tunnel de 2 km, avec deux tubes et deux voies par tube, en contexte périurbain.
/show
/profile
/details
/accept
/run
/quit
```

`/profile` propose des hypothèses de démonstration pour les champs manquants. Lire `/details` avant `/accept`. L'acceptation ne constitue pas une validation physique des hypothèses. Le profil de calcul rapide couvre 7 jours, avec un pas de 60 minutes, 3 simulations et une graine de 42.

Chaque demande en langage naturel consomme une tentative Gemini ; les commandes commençant par `/` sont locales. `/run` lance le calcul explicitement. Les réponses comprennent des phrases et un schéma textuel ; les résultats chiffrés viennent de TLS.

Les fichiers sont écrits dans `runs/` : CSV, `manifest.json` et `conversation.json`. L'historique contient vos demandes : relire avant de partager. Aucune clé n'y est enregistrée.

## 4. Tester sans API et transmettre un retour

Pour vérifier uniquement le calcul local, démarrer le terminal puis saisir `/profile`, `/accept`, `/run`, `/quit`, sans phrase naturelle : aucun appel Gemini.

Pour les tests logiciels :

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[dev,tls]'
& .\.venv\Scripts\python.exe -m pytest -q
git rev-parse HEAD
```

Transmettre le commit, la version Python, la demande testée, la réponse et l'éventuelle erreur. Ne transmettre aucune clé API. Les versions testées en développement sont dans `requirements-tested.txt` ; les dépendances d'installation ne sont pas toutes figées.

## Limites actuelles

- Un seul scénario à la fois ; une comparaison A/B déclenche une clarification.
- « Éclairage fort/faible » ne correspond pas à un paramètre d'intensité exposé par ce PoC.
- Données synthétiques, sans calibration terrain ; l'annualisation extrapole la période simulée.
- TLS seul est exécutable dans le terminal ; LQL-Equiv, pvlib et la voix restent des évolutions.
- Une erreur API n'entraîne aucun nouvel essai automatique. Sans clé, les commandes locales restent disponibles.
