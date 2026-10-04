# Installation Windows

## Package de validation

1. Décompressez complètement l’archive.
2. Double-cliquez sur `Installer.cmd` et attendez la fin de la vérification.
3. Ouvrez `WebSemantic.cmd` et choisissez TLS.

Les composants compatibles présents sont conservés. Le lanceur n’installe rien ; s’il détecte un manque, il invite à relancer l’installateur. Le guide fourni propose les quatre essais de validation.

La configuration privée fournie pour l’essai est lue automatiquement. Ne publiez pas l’archive ni son fichier `.env`.

## Installation depuis GitHub

Python 3.10 ou plus récent et Git sont nécessaires. Depuis le répertoire choisi :

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls]"
```

Le clone public ne contient aucune clé. Configurez `GEMINI_API_KEY` dans les variables d’environnement utilisateur Windows, ou dans un fichier `.env` privé à la racine du clone. Fermez puis rouvrez le terminal après une modification des variables utilisateur. N’incluez jamais la clé dans un retour de test ou un commit.

```powershell
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

L’interprétation nécessite Internet et un accès au service Gemini. Le simulateur TLS est fourni dans une révision fixée. Pour vérifier uniquement le calcul local, ouvrez TLS puis utilisez `/p`, `/v`, `/q` : aucune phrase n’est envoyée au service et la validation admissible lance le calcul.

## Retour de validation

Transmettez la demande, la réponse, le résultat attendu et le dossier du calcul. Les CSV et le manifeste permettent de retrouver les paramètres et les unités. Ne joignez aucun fichier de configuration contenant une clé.
