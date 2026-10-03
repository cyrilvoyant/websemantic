@echo off
set "WEBSEMANTIC_INSTALL_ONLY=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0application\installer-et-lancer.ps1"
if errorlevel 1 (pause) else (echo Installation terminee. Ouvrez WebSemantic_TLS.cmd.& pause)
