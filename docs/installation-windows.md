# Installation Windows

## Package

Décompressez l’archive et ouvrez `Installer.cmd` une fois. Ensuite, ouvrez `WebSemantic.cmd` et choisissez TLS. Le lanceur indique si un composant manque ; l’installation conserve les composants compatibles.

La configuration de l’essai est lue automatiquement. Gardez l’archive et le fichier `.env` privés.

## Dépôt public

Python 3.10+ et Git sont nécessaires.

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls]"
```

Configurez `GEMINI_API_KEY` dans vos variables d’environnement ou dans un `.env` privé. Rouvrez le terminal après une modification des variables Windows.

```powershell
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

Le dialogue utilise Internet. Pour vérifier le calcul local avec les commandes, choisissez TLS puis `/p`, `/v`, `/q`.

Pour un retour de test, joignez la demande, la réponse et le dossier du calcul, sans fichier contenant une clé.
