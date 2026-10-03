$ErrorActionPreference = 'Stop'
if ($PSScriptRoot.StartsWith('\\')) {
    $localApplication = Join-Path $env:LOCALAPPDATA 'WebSemantic_TLS\application'
    New-Item -ItemType Directory -Path $localApplication -Force | Out-Null
    Write-Host 'Dossier réseau détecté. Préparation du programme sur le disque local...'
    & robocopy $PSScriptRoot $localApplication /E /XD .venv runs /R:1 /W:1 /NFL /NDL /NJH /NJS
    if ($LASTEXITCODE -ge 8) {
        Write-Host 'Copie locale impossible. Décompressez le package sur le disque C:.' -ForegroundColor Red
        exit 1
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $localApplication 'installer-et-lancer.ps1')
    exit $LASTEXITCODE
}
Set-Location -LiteralPath $PSScriptRoot
function Refresh-Tools {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    foreach ($folder in @("$env:LOCALAPPDATA\Programs\Git\cmd", "$env:ProgramFiles\Git\cmd")) {
        if (Test-Path -LiteralPath $folder) { $env:Path += ';' + $folder }
    }
}
function Install-Tool($packageId) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Installation automatique indisponible : installez App Installer (winget) depuis le Microsoft Store, puis relancez.'
    }
    Write-Host "Installation de $packageId..."
    & winget install --id $packageId --exact --source winget --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Installation de $packageId échouée. Vérifiez les droits et la connexion Internet." }
    Refresh-Tools
}
function Find-Python {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3 -c 'import sys; print(sys.executable) if sys.version_info >= (3,10) else None' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $candidates += [string]$found }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += (Get-Command python).Source }
    $candidates += "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        & $candidate -c 'import sys,venv; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}
try {
    Refresh-Tools
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Install-Tool 'Git.Git'
    }
    & git --version
    if ($LASTEXITCODE -ne 0) { throw 'Git ne fonctionne pas après installation.' }
    $pythonExecutable = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExecutable)) {
        $basePython = Find-Python
        if (-not $basePython) {
            Install-Tool 'Python.Python.3.12'
            $basePython = Find-Python
        }
        if (-not $basePython) { throw 'Python reste introuvable. Fermez puis relancez le lanceur.' }
        Write-Host 'Premier lancement : création de l environnement Python...'
        & $basePython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Création de l environnement impossible.' }
    }
    & $pythonExecutable -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 ou supérieur est requis.' }
    $installationMarker = Join-Path $PSScriptRoot '.venv\websemantic-ready'
    & $pythonExecutable -c 'import yaml,numpy,pandas,websemantic.cli' 2>$null
    $dependenciesReady = $LASTEXITCODE -eq 0
    if (-not (Test-Path -LiteralPath $installationMarker) -or -not $dependenciesReady) {
        Write-Host 'Installation des dépendances (connexion Internet nécessaire)...'
        & $pythonExecutable -m pip install -e '.[tls]'
        if ($LASTEXITCODE -ne 0) { throw 'Installation échouée. Vérifiez la connexion puis relancez.' }
        New-Item -ItemType File -Path $installationMarker -Force | Out-Null
    }
    & $pythonExecutable -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dépendances incohérentes. Supprimez le dossier .venv puis relancez.' }
    $backendPath = Join-Path $PSScriptRoot 'external\tunnel-load-simulator'
    if (-not (Test-Path -LiteralPath (Join-Path $backendPath 'src\tunnel_load_simulator\simulator.py'))) {
        & git submodule update --init --recursive
        if ($LASTEXITCODE -ne 0) { throw 'Les sources TLS sont absentes. Décompressez entièrement le package.' }
    }
    @"
import subprocess, yaml
from pathlib import Path
d = yaml.safe_load(Path('descriptors/tls/descriptor.yaml').read_text(encoding='utf-8'))
p = 'external/tunnel-load-simulator'
c = subprocess.check_output(['git', '-C', p, 'rev-parse', 'HEAD'], text=True).strip()
s = subprocess.check_output(['git', '-C', p, 'status', '--porcelain', '--untracked-files=no'], text=True)
assert c == d['software']['commit'] and not s, 'Version TLS incorrecte ou sources modifiees'
"@ | & $pythonExecutable -
    if ($LASTEXITCODE -ne 0) { throw 'Le contrôle du simulateur TLS a échoué.' }
    Write-Host 'Démarrage de WebSemantic_TLS. /help pour les commandes, /quit pour sortir.'
    & $pythonExecutable -m websemantic.cli chat --model tls
    if ($LASTEXITCODE -ne 0) { throw 'Le programme s est arrêté avec une erreur.' }
} catch {
    Write-Host ('Erreur : ' + $_.Exception.Message) -ForegroundColor Red
    Read-Host 'Appuyez sur Entrée pour fermer'
    exit 1
}
