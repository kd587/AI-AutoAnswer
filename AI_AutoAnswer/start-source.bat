@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv\Scripts\python.exe. See README.md for setup.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
