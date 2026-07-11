@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "backend\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\backend\.venv\Scripts\python.exe"

echo.
echo [1/5] Checking Python syntax...
"%PYTHON_EXE%" -m compileall -q backend\ai_backtester backend\ai_research backend\main_ai.py
if errorlevel 1 goto :failed

echo [2/5] Running AI backtester smoke check...
pushd backend
"%PYTHON_EXE%" -m ai_backtester.smoke_check
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [3/5] Running multi-agent research smoke check...
pushd backend
"%PYTHON_EXE%" -m ai_research.smoke_check
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [4/5] Checking JavaScript syntax when Node.js is available...
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found, JavaScript syntax check skipped.
) else (
  node --check frontend\ai-backtest.js
  if errorlevel 1 goto :failed
  node --check frontend\demo-mode.js
  if errorlevel 1 goto :failed
  echo [5/5] Running frontend fallback risk check...
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
