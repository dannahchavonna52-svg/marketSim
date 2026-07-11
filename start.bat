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

"%PYTHON_EXE%" --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found. Install Python or create backend\.venv first.
  pause
  exit /b 1
)

cd /d "%~dp0backend"

if "%~1"=="--check" (
  echo start.bat syntax ok
  echo Backend path: %CD%
  echo Python: %PYTHON_EXE%
  "%PYTHON_EXE%" -c "import sys; print(sys.version)"
  exit /b 0
)

netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if not errorlevel 1 (
  echo.
  echo ERROR: Port 8000 is already in use. MarketSim may already be running.
  echo Open http://127.0.0.1:8000 or close the existing process first.
  pause
  exit /b 1
)

echo.
echo MarketSim Fund App is starting...
echo.
echo PC URL: http://127.0.0.1:8000
echo Phone URL: use your PC IPv4 address, for example http://192.168.1.8:8000
echo.
ipconfig | findstr /i "IPv4"
echo.
echo If the phone cannot open it, check same Wi-Fi and Windows Firewall.
echo.
"%PYTHON_EXE%" -m uvicorn main_ai:app --host 0.0.0.0 --port 8000

pause
