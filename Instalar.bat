@echo off
REM Cria o ambiente Python 3.11 (.venv) e instala as dependencias do projeto.
REM Requer Python 3.11: winget install --id Python.Python.3.11 -e --scope user
cd /d "%~dp0"
py -3.11 --version >nul 2>&1 || (
    echo Python 3.11 nao encontrado. Instale com:
    echo   winget install --id Python.Python.3.11 -e --scope user
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements_win.txt
echo.
echo Instalacao concluida. Para abrir o programa, de dois cliques em "Abrir Pokerbot.bat".
pause
