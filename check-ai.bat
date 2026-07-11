@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "backend\.venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\backend\.venv\Scripts\python.exe"

echo.
echo [1/6] Checking Python syntax...
"%PYTHON_EXE%" -m compileall -q backend\ai_backtester backend\ai_research backend\main_ai.py
if errorlevel 1 goto :failed

echo [2/6] Running AI backtester smoke check...
pushd backend
"%PYTHON_EXE%" -m ai_backtester.smoke_check
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [3/6] Running multi-agent research smoke check...
pushd backend
"%PYTHON_EXE%" -m ai_research.smoke_check
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [4/6] Checking JavaScript syntax when Node.js is available...
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found, JavaScript syntax check skipped.
) else (
  node --check frontend\ai-backtest.js
  if errorlevel 1 goto :failed
  node --check frontend\demo-mode.js
  if errorlevel 1 goto :failed
  node --check frontend\learning-content.js
  if errorlevel 1 goto :failed
  node --check frontend\learning.js
  if errorlevel 1 goto :failed
  echo [5/6] Running frontend fallback risk check...
  node frontend\ai-backtest-smoke-check.js
  if errorlevel 1 goto :failed
  echo [6/6] Running beginner learning MVP check...
  node frontend\learning-smoke-check.js
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
