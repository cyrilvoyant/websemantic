@echo off
set "appPath=%~dp0application"
set "WEBSEMANTIC_OUTPUT_DIR=%~dp0Resultats"
if "%appPath:~0,2%"=="\\" set "appPath=%LOCALAPPDATA%\WebSemantic_TLS\application"
if not exist "%appPath%\.venv\Scripts\python.exe" (
 echo L environnement Python de WebSemantic_TLS est absent.
 echo Lancez Installer.cmd pour installer les composants necessaires.
 pause
 exit /b 1
)
set "PYTHONUTF8=1"
if not exist "%appPath%\verifier-installation.py" (
 echo La verification de l installation est absente. Decompressez le package complet puis lancez Installer.cmd.
 pause
 exit /b 1
)
"%appPath%\.venv\Scripts\python.exe" "%appPath%\verifier-installation.py"
if errorlevel 1 (
 echo Le lancement est arrete. Lancez Installer.cmd pour verifier et reparer l installation.
 pause
 exit /b 1
)
pushd "%appPath%"
"%appPath%\.venv\Scripts\python.exe" -m websemantic.cli chat --model tls --max-calls 0 --open-results
set "result=%errorlevel%"
popd
if not "%result%"=="0" pause
