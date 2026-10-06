$ErrorActionPreference = 'Stop'
$localApplication = Join-Path $env:LOCALAPPDATA 'WebSemantic_TLS\application'
if ([IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') -ine [IO.Path]::GetFullPath($localApplication).TrimEnd('\')) {
    New-Item -ItemType Directory -Path $localApplication -Force | Out-Null
    Write-Host 'Préparation du programme dans son dossier permanent...'
    & robocopy $PSScriptRoot $localApplication /E /XD .venv runs /R:1 /W:1 /NFL /NDL /NJH /NJS
    if ($LASTEXITCODE -ge 8) {
        Write-Host 'Copie du programme impossible. Vérifiez les droits du dossier local.' -ForegroundColor Red
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
    & winget install --id $packageId --architecture x64 --exact --source winget --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Installation de $packageId échouée. Vérifiez les droits et la connexion Internet." }
    Refresh-Tools
}
function Find-Python {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3 -c 'import sys; print(sys.executable) if sys.version_info >= (3,12) else None' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $candidates += [string]$found }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += (Get-Command python).Source }
    foreach ($pythonHome in @("$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles")) {
        if (Test-Path -LiteralPath $pythonHome) {
            Get-ChildItem -LiteralPath $pythonHome -Directory -Filter 'Python*' -ErrorAction SilentlyContinue | ForEach-Object {
                $candidates += Join-Path $_.FullName 'python.exe'
            }
        }
    }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        & $candidate -c 'import sys,venv,struct; sys.exit(0 if sys.version_info >= (3,12) and struct.calcsize(chr(80)) == 8 else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}
# Windows PowerShell treats native stderr as an ErrorRecord. Inspect exit codes
# instead of aborting at the first line of a Python traceback or import probe.
$ErrorActionPreference = 'Continue'
try {
    Refresh-Tools
    $pythonExecutable = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $environmentReady = $false
    if (Test-Path -LiteralPath $pythonExecutable) {
        & $pythonExecutable -c 'import sys,struct; sys.exit(0 if sys.version_info >= (3,12) and struct.calcsize(chr(80)) == 8 else 1)' 2>$null
        $environmentReady = $LASTEXITCODE -eq 0
    }
    if (-not $environmentReady) {
        $basePython = Find-Python
        if (-not $basePython) {
            Install-Tool 'Python.Python.3.12'
            $basePython = Find-Python
        }
        if (-not $basePython) { throw 'Python reste introuvable. Fermez puis relancez le lanceur.' }
        $environmentPath = Join-Path $PSScriptRoot '.venv'
        if (Test-Path -LiteralPath $environmentPath) {
            Rename-Item -LiteralPath $environmentPath -NewName ('.venv-incomplete-' + [guid]::NewGuid().ToString('N')) -ErrorAction Stop
        }
        Write-Host 'Premier lancement : création de l environnement Python...'
        Write-Host "Python utilisé : $basePython"
        $creationLog = Join-Path $PSScriptRoot 'installation-diagnostic.txt'
        & $basePython -m venv .venv 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $creationLog
        if ($LASTEXITCODE -ne 0) { throw "Création Python impossible. Détail complet dans $creationLog" }
    }
    & $pythonExecutable -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 ou supérieur est requis.' }
    & $pythonExecutable (Join-Path $PSScriptRoot 'verifier-installation.py') --dependencies-only
    $dependenciesReady = $LASTEXITCODE -eq 0
    if (-not $dependenciesReady) {
        Write-Host 'Installation des dépendances (connexion Internet nécessaire)...'
        & $pythonExecutable -m pip --version 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            & $pythonExecutable -m ensurepip
            if ($LASTEXITCODE -ne 0) { throw 'pip est absent et sa réparation a échoué.' }
        }
        $dependencyLog = Join-Path $PSScriptRoot 'installation-diagnostic.txt'
        & $pythonExecutable -c 'import sys,platform,struct; print(sys.version); print(struct.calcsize(chr(80))*8); print(platform.machine())' 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $dependencyLog -Append
        & $pythonExecutable -m pip install --upgrade pip 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $dependencyLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Préparation de pip impossible. Détail dans $dependencyLog" }
        & $pythonExecutable -m pip install --only-binary=:all: -e '.[tls,atmosphere]' 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $dependencyLog -Append
        if ($LASTEXITCODE -ne 0) { throw "Installation des dépendances échouée (compatibilité Python, accès aux paquets ou réseau). Détail complet dans $dependencyLog" }
        & $pythonExecutable (Join-Path $PSScriptRoot 'verifier-installation.py') --dependencies-only
        if ($LASTEXITCODE -ne 0) { throw 'Les composants restent incomplets après installation.' }
    } else {
        Write-Host 'Composants déjà présents et compatibles : aucune installation nécessaire.'
    }
    & $pythonExecutable -m pip --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $pythonExecutable -m pip check
        if ($LASTEXITCODE -ne 0) { throw 'Dépendances incohérentes. Vérifiez les versions indiquées par pip check.' }
    }
    & $pythonExecutable (Join-Path $PSScriptRoot 'verifier-installation.py') --smoke
    if ($LASTEXITCODE -ne 0) { throw 'Un test de calcul a échoué. L installation reste à vérifier.' }
    Write-Host 'Vérification terminée. Ouvrez WebSemantic.cmd pour utiliser le programme.'
    exit 0
} catch {
    Write-Host ('Erreur : ' + $_.Exception.Message) -ForegroundColor Red
    Read-Host 'Appuyez sur Entrée pour fermer'
    exit 1
}
