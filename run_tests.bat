@echo off
cd /d "%~dp0"
if "%1"=="visual" (
    shift
    venv\Scripts\python.exe -m pytest --headed --slow-mo 600 %*
) else (
    venv\Scripts\python.exe -m pytest %*
)
