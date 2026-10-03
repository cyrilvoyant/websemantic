@echo off
set "appPath=%~dp0application"
set "WEBSEMANTIC_OUTPUT_DIR=%~dp0Resultats"
if "%appPath:~0,2%"=="\\" set "appPath=%LOCALAPPDATA%\WebSemantic_TLS\application"
if not exist "%appPath%\.venv\Scripts\python.exe" (
 echo Lancez Installer.cmd une premiere fois.
 pause
 exit /b 1
)
set "PYTHONUTF8=1"
pushd "%appPath%"
"%appPath%\.venv\Scripts\python.exe" -m websemantic.cli chat --model tls --max-calls 0 --open-results
set "result=%errorlevel%"
popd
if not "%result%"=="0" pause
