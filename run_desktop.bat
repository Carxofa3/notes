@echo off
REM Launcher script for Notes Workstation Desktop (Windows)
setlocal

cd /d "%~dp0"
echo [Notes Desktop] Starting application environment...

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop.py %*
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" desktop.py %*
) else (
    python desktop.py %*
)

endlocal
