@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.3.3 - Install or Repair
echo.

set "FROMZIP="
echo %CD% | find /I "\AppData\Local\Temp" >nul && set "FROMZIP=1"
if defined TEMP echo %CD% | find /I "%TEMP%" >nul && set "FROMZIP=1"
if defined TMP echo %CD% | find /I "%TMP%" >nul && set "FROMZIP=1"
if defined FROMZIP goto :ZIPWINDOW

if not exist "%~dp0repair.ps1" goto :MISSING
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0repair.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Repair did not finish. See INSTALL-OR-REPAIR.log in this folder.
  pause
)
exit /b %RC%

:MISSING
echo repair.ps1 is missing.
echo Download the complete Windows zip, right-click it, and choose Extract All.
echo Then double-click INSTALL-OR-REPAIR.bat in the extracted folder.
pause
exit /b 1

:ZIPWINDOW
echo You opened the installer from INSIDE the zip window.
echo Right-click ClassInterpreter-windows-0.3.3.zip and choose Extract All.
echo Then double-click INSTALL-OR-REPAIR.bat in the extracted folder.
pause
exit /b 1
