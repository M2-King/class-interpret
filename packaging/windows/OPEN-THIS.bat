@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.3.3
echo Folder: %CD%
echo.

set "FROMZIP="
echo %CD% | find /I "\AppData\Local\Temp" >nul && set "FROMZIP=1"
if defined TEMP echo %CD% | find /I "%TEMP%" >nul && set "FROMZIP=1"
if defined TMP echo %CD% | find /I "%TMP%" >nul && set "FROMZIP=1"
if defined FROMZIP goto :ZIPWINDOW

if exist "%~dp0ClassInterpreter-0.3.3\Start.bat" (
  cd /d "%~dp0ClassInterpreter-0.3.3"
  call Start.bat
  exit /b %ERRORLEVEL%
)

if exist "%~dp0Start.bat" (
  call Start.bat
  exit /b %ERRORLEVEL%
)

echo Could not find Start.bat.
echo Right-click ClassInterpreter-windows-0.3.3.zip, choose Extract All,
echo then double-click OPEN-THIS.bat in the new folder.
echo.
pause
exit /b 1

:ZIPWINDOW
echo You opened a file from INSIDE the zip window.
echo Windows copied it to Temp, so the app cannot run.
echo This is not a broken laptop or GPU.
echo.
echo 1. Close this window.
echo 2. Right-click ClassInterpreter-windows-0.3.3.zip
echo 3. Choose Extract All
echo 4. Open the new folder
echo 5. Double-click OPEN-THIS.bat
echo.
pause
exit /b 1
