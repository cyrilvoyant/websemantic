$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw 'Git est requis. Installez Git puis relancez ce fichier.'
    }
    $pythonExecutable = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExecutable)) {
        Write-Host 'Premier lancement : création de l environnement Python...'
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv .venv
        } else {
            throw 'Python est requis (3.10 minimum, 3.12 conseillé). Installez-le puis relancez.'
        }
        if ($LASTEXITCODE -ne 0) { throw 'Création de l environnement impossible.' }
    }
    & $pythonExecutable -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 ou supérieur est requis.' }
    $installationMarker = Join-Path $PSScriptRoot '.venv\websemantic-ready'
    if (-not (Test-Path -LiteralPath $installationMarker)) {
        Write-Host 'Installation des dépendances (connexion Internet nécessaire)...'
        & $pythonExecutable -m pip install -e '.[tls]'
        if ($LASTEXITCODE -ne 0) { throw 'Installation échouée. Vérifiez la connexion puis relancez.' }
        New-Item -ItemType File -Path $installationMarker -Force | Out-Null
    }
    Write-Host 'Démarrage de WebSemantic_TLS. /help pour les commandes, /quit pour sortir.'
    & $pythonExecutable -m websemantic.cli chat --model tls
    if ($LASTEXITCODE -ne 0) { throw 'Le programme s est arrêté avec une erreur.' }
} catch {
    Write-Host ('Erreur : ' + $_.Exception.Message) -ForegroundColor Red
    Read-Host 'Appuyez sur Entrée pour fermer'
    exit 1
}
