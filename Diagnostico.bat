@echo off
REM Verifica instalacao, bibliotecas e acesso ao servidor do desenvolvedor. Salva o resultado em diagnostico.txt
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Rode primeiro: Instalar.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" ferramentas\diagnostico.py
echo.
echo Resultado salvo em diagnostico.txt
pause
