@echo off
REM Abre o PokerBot original usando o ambiente Python 3.11 instalado em .venv
cd /d "%~dp0poker"
set PYTHONPATH=%~dp0
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Rode primeiro: Instalar.bat
    pause
    exit /b 1
)
REM Verifica se o servidor do desenvolvedor responde (sem ele o programa nao abre)
"%~dp0.venv\Scripts\python.exe" "%~dp0ferramentas\diagnostico.py" --antes-de-abrir
if errorlevel 10 exit /b 10
"%~dp0.venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo O PokerBot fechou com erro. Para um diagnostico, de dois cliques em "Diagnostico.bat".
    echo Log de erros: poker\log\deepmind_pokerbot_errors.log
    pause
)
