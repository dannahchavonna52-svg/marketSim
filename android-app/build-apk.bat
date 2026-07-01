@echo off
setlocal
cd /d "%~dp0"

echo Building MarketSim Fund App APK...
echo.

where java >nul 2>nul
if errorlevel 1 (
  echo Missing Java JDK.
  echo Please install Android Studio or JDK 17 first.
  pause
  exit /b 1
)

where gradle >nul 2>nul
if errorlevel 1 (
  echo Missing Gradle command.
  echo Open this folder in Android Studio and use Build APK, or install Gradle.
  pause
  exit /b 1
)

gradle assembleDebug

if exist "app\build\outputs\apk\debug\app-debug.apk" (
  echo.
  echo APK ready:
  echo %CD%\app\build\outputs\apk\debug\app-debug.apk
) else (
  echo.
  echo Build did not produce APK. Check the Gradle output above.
)

pause
