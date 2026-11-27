@echo off
REM Abre o Pokerbot usando o ambiente Python 3.11 instalado em .venv
cd /d "%~dp0poker"
set PYTHONPATH=%~dp0
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Rode primeiro: Instalar.bat
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" main.py
if errorlevel 1 pause
