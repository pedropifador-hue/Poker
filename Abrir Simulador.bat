@echo off
REM Abre o Simulador Offline (nao precisa de internet nem do servidor do desenvolvedor)
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Ambiente nao encontrado. Rode primeiro: Instalar.bat
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m simulador.janela
