# Tester WebSemantic_TLS sur un autre PC Windows

Ce guide permet d'installer la version de test sur Windows. Vous décrivez le tunnel dans PowerShell ; Gemini extrait les paramètres et TLS calcule la consommation. Les deux étapes restent séparées : vous vérifiez les paramètres avant de lancer le calcul.

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

Créez votre clé dans Google AI Studio et gardez-la sur votre machine. Le quota utilisé sera celui de votre projet Google.

Dans le même PowerShell, saisir la clé de façon masquée :

```powershell
$geminiSecret = Read-Host 'Votre clé Gemini (saisie masquée)' -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $geminiSecret).Password
Remove-Variable geminiSecret
```

Cette configuration dure uniquement pendant la session PowerShell. Le programme peut aussi lire la variable utilisateur Windows `GEMINI_API_KEY`. Ne pas saisir la clé dans la conversation.

Le modèle par défaut est `gemini-3.5-flash-lite`, utilisé lors des essais de développement. Son accès dépend du compte ; un modèle autorisé peut être choisi avec `--llm NOM_DU_MODELE`. Les limites et la facturation sont celles du projet Google du testeur.

## 3. Converser et lancer un calcul

Pour le test temporaire avec la clé fournie par Cyril, placez le fichier privé `.env` reçu séparément à la racine du clone, à côté de `pyproject.toml`. Vous pouvez alors passer l'étape 2. Le programme lit ce fichier lors du premier appel Gemini. Une variable `GEMINI_API_KEY` déjà présente dans la session PowerShell reste prioritaire. Le fichier contient une clé en clair : ne le joignez pas aux retours de test et ne le publiez pas. Il est exclu de Git. Le modèle et les quotas restent ceux du projet associé à cette clé. Supprimez le fichier à la fin de l'essai ; la révocation de la clé se fait dans Google AI Studio.

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

Il manque généralement des paramètres après la première phrase. `/profile` propose des valeurs pour un essai ; `/details` permet de les lire et `/accept` de les retenir. Ce sont des hypothèses de démonstration, pas des données du tunnel. Le calcul couvre 7 jours, avec un pas de 60 minutes, 3 simulations et une graine de 42.

Chaque phrase envoyée fait un appel à Gemini. Les commandes `/show`, `/profile`, `/accept` et `/run` sont locales. Le calcul commence seulement avec `/run` ; ses résultats viennent de TLS.

Les fichiers sont écrits dans `runs/` : CSV, `manifest.json` et `conversation.json`. L'historique contient vos demandes : relire avant de partager. Aucune clé n'y est enregistrée.

## 4. Tester sans API et transmettre un retour

Pour vérifier uniquement le calcul local, démarrer le terminal puis saisir `/profile`, `/accept`, `/run`, `/quit`, sans phrase naturelle : aucun appel Gemini.

Pour les tests logiciels :

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[dev,tls]'
& .\.venv\Scripts\python.exe -m pytest -q
git rev-parse HEAD
```

Pour un retour exploitable, envoyez le commit affiché, la version de Python et la demande qui pose problème, avec la réponse ou le message d'erreur. Les versions utilisées en développement sont dans `requirements-tested.txt` ; l'installation peut récupérer des versions plus récentes.

## Limites actuelles

- Un seul scénario à la fois ; une comparaison A/B déclenche une clarification.
- « Éclairage fort/faible » ne correspond pas à un paramètre d'intensité exposé par ce PoC.
- Données synthétiques, sans calibration terrain ; l'annualisation extrapole la période simulée.
- TLS seul est exécutable dans le terminal ; LQL-Equiv, pvlib et la voix restent des évolutions.
- Une erreur API n'entraîne aucun nouvel essai automatique. Sans clé, les commandes locales restent disponibles.
