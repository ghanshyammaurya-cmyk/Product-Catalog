@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo Virtual environment not found. Create venv and install requirements first.
  pause
  exit /b 1
)

"venv\Scripts\python.exe" launch_qa_tool.py
endlocal
