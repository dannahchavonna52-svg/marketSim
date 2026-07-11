@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "backend\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\backend\.venv\Scripts\python.exe"

echo.
echo [1/4] Checking Python syntax...
"%PYTHON_EXE%" -m compileall -q backend\ai_backtester backend\main_ai.py
if errorlevel 1 goto :failed

echo [2/4] Running AI backtester smoke check...
pushd backend
"%PYTHON_EXE%" -m ai_backtester.smoke_check
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [3/4] Checking JavaScript syntax when Node.js is available...
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found, JavaScript syntax check skipped.
) else (
  node --check frontend\ai-backtest.js
  if errorlevel 1 goto :failed
  node --check frontend\demo-mode.js
  if errorlevel 1 goto :failed
  echo [4/4] Running frontend fallback risk check...
  node frontend\ai-backtest-smoke-check.js
  if errorlevel 1 goto :failed
)

echo.
echo All available AI checks passed.
echo You can now run start.bat or start-demo.bat.
pause
exit /b 0

:failed
echo.
echo AI check failed. Copy the error above into Codex for repair.
pause
exit /b 1
