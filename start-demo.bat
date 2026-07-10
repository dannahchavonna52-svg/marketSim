@echo off
setlocal
cd /d "%~dp0backend"

if not exist "data" mkdir "data"
if not exist ".tmp" mkdir ".tmp"

set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"
set "PYTHONDONTWRITEBYTECODE=1"

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

set "DEMO_URL=http://127.0.0.1:8000/?demo=1&fund=014855&focus=1"

echo.
echo MarketSim video demo is starting...
echo Demo URL: %DEMO_URL%
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process $env:DEMO_URL"
"%PYTHON_EXE%" -m uvicorn main_ai:app --host 0.0.0.0 --port 8000

pause
