@echo off
rem De dois cliques para abrir o painel. Na primeira vez instala o que falta.
cd /d "%~dp0"
where speedtest >nul 2>nul || winget install -e --id Ookla.Speedtest.CLI
if not exist .venv\Scripts\python.exe (
    python -m venv .venv || (echo Instale o Python em https://www.python.org/downloads/ e rode de novo. & pause & exit /b 1)
)
.venv\Scripts\python -c "import nicegui" 2>nul || .venv\Scripts\python -m pip install nicegui
.venv\Scripts\python app.py
