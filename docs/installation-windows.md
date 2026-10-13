# Installation on Windows

## Package

Unzip the archive and open `Installer.cmd` once. Then open `WebSemantic.cmd` and choose TLS. The launcher reports any
missing component; the installation keeps the compatible ones.

The trial configuration is read automatically. Keep the archive and the `.env` file private.

## Public repository

Python 3.12+ and Git are needed.

```powershell
git clone --recurse-submodules https://github.com/cyrilvoyant/websemantic.git
cd websemantic
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[tls]"
```

Set `GEMINI_API_KEY` in your environment variables or in a private `.env` file. Reopen the terminal after changing
Windows variables.

```powershell
& .\.venv\Scripts\python.exe -m websemantic.cli chat
```

The dialogue needs an Internet connection. To check the local calculation with commands, choose TLS, then `/p`, `/v`,
`/q`.

To report a test, attach the request, the answer and the result folder, without any file that contains a key.
