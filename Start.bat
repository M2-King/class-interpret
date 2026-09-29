@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.3.1
echo Folder: %CD%
echo If this laptop already ran Class Interpreter, use THAT old folder.
echo Do not replace a working copy with a new unzip from Downloads.
echo First run may download Python 3.12. Keep this window open.
echo If the first line says 0.2.5-0.2.9, you opened an old zip. Close this window.
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
  echo 1. Switch to a phone hotspot and double-click Start.bat again.
  echo 2. Keep this window open; first run downloads Python 3.12 automatically.
  echo 3. Do not double-click start.ps1.
  echo.
  pause
  exit /b 1
)

endlocal
