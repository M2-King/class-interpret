@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.2.5
echo.

if not exist "%~dp0start.ps1" (
  echo start.ps1 is missing.
  echo Unzip ClassInterpreter-windows.zip and open the ClassInterpreter folder.
  echo Delete any old unzipped copy first.
  echo.
  pause
  exit /b 1
)

where powershell >nul 2>&1
if errorlevel 1 (
  echo PowerShell was not found. Windows 10 and 11 include it.
  echo.
  pause
  exit /b 1
)

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0start.ps1' -ErrorAction SilentlyContinue"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
  echo.
  echo Launch failed.
  echo 1. Delete old unzipped folders, then download ClassInterpreter-windows.zip again.
  echo 2. Double-click Start.bat. Do not double-click start.ps1.
  echo 3. Install Python 3.10-3.12 from python.org and check Add python.exe to PATH.
  echo 4. Campus Wi-Fi: switch to a phone hotspot.
  echo.
  pause
  exit /b 1
)

endlocal
