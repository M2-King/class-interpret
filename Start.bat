@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.3.2
echo Folder: %CD%
echo If this laptop already ran Class Interpreter, use THAT old folder.
echo Do not replace a working copy with a new unzip from Downloads.
echo First run may download Python 3.12. Keep this window open.
echo If the first line says 0.2.5-0.3.1, you opened an old zip. Close this window.
echo.

set "FROMZIP="
echo %CD% | find /I "\AppData\Local\Temp" >nul && set "FROMZIP=1"
if defined TEMP echo %CD% | find /I "%TEMP%" >nul && set "FROMZIP=1"
if defined TMP echo %CD% | find /I "%TMP%" >nul && set "FROMZIP=1"
if defined FROMZIP (
  echo.
  echo You opened Start.bat from INSIDE the zip.
  echo Windows put it in a Temp folder, so it cannot run.
  echo This is not a broken laptop.
  echo.
  echo 1. Close this window.
  echo 2. Right-click ClassInterpreter-windows-0.3.2.zip
  echo 3. Choose Extract All
  echo 4. Open the new folder
  echo 5. Double-click OPEN-THIS.bat
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0start.ps1" (
  echo start.ps1 is missing.
  echo Right-click ClassInterpreter-windows-0.3.2.zip, Extract All, then OPEN-THIS.bat.
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0server.py" (
  echo server.py is missing. This folder is incomplete.
  echo Delete it, Extract All the 0.3.2 zip, then double-click OPEN-THIS.bat.
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
  echo Launch failed. This is usually Extract All, an old folder, or campus Wi-Fi.
  echo It is not the laptop GPU.
  echo 1. If the path contains Temp, Extract All first, then OPEN-THIS.bat.
  echo 2. If this laptop already worked, close this and open the old folder.
  echo 3. Switch to a phone hotspot and double-click Start.bat again.
  echo 4. Do not double-click start.ps1.
  echo.
  pause
  exit /b 1
)

endlocal
