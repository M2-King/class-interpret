@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Class Interpreter 0.3.3
echo Folder: %CD%
echo.
echo Windows use:
echo A  If this laptop already worked, close this and open the OLD folder Start.bat
echo B  New copy: Extract All the zip, then OPEN-THIS.bat. Keep this window open.
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
  echo 2. Right-click ClassInterpreter-windows-0.3.3.zip
  echo 3. Choose Extract All
  echo 4. Open the new folder
  echo 5. Double-click OPEN-THIS.bat
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0win_bootstrap.py" goto :NEEDPS
if not exist "%~dp0server.py" (
  echo server.py is missing. Extract All ClassInterpreter-windows-0.3.3.zip first.
  pause
  exit /b 1
)

if exist "%~dp0.venv\Scripts\python.exe" goto :VENV
if exist "%~dp0..\.venv\Scripts\python.exe" goto :PARENTVENV
if exist "%~dp0.runtime\python\python.exe" goto :BUNDLE
goto :NEEDPS

:VENV
echo Using the existing .venv on this laptop.
"%~dp0.venv\Scripts\python.exe" -u "%~dp0win_bootstrap.py"
goto :CHECK

:PARENTVENV
echo Using the existing .venv in the parent folder.
"%~dp0..\.venv\Scripts\python.exe" -u "%~dp0win_bootstrap.py"
goto :CHECK

:BUNDLE
echo Using bundled Python. First run may take a few minutes.
where powershell >nul 2>&1
if not errorlevel 1 (
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
)
"%~dp0.runtime\python\python.exe" -u "%~dp0win_bootstrap.py"
goto :CHECK

:NEEDPS
if not exist "%~dp0start.ps1" (
  echo start.ps1 is missing. Extract All ClassInterpreter-windows-0.3.3.zip, then OPEN-THIS.bat.
  pause
  exit /b 1
)
where powershell >nul 2>&1
if errorlevel 1 (
  echo PowerShell was not found. Windows 10 and 11 include it.
  pause
  exit /b 1
)
echo Bundled Python was not found. Trying PowerShell download...
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0start.ps1' -ErrorAction SilentlyContinue"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
goto :CHECK

:CHECK
if errorlevel 1 (
  echo.
  echo Launch failed.
  echo 1. Do not open files inside the zip window. Right-click - Extract All - OPEN-THIS.bat
  echo 2. If this laptop already worked, use the old folder instead of Downloads.
  echo 3. Campus Wi-Fi: phone hotspot, then OPEN-THIS.bat again. Keep the black window open.
  echo 4. The first line must say Class Interpreter 0.3.3
  echo.
  pause
  exit /b 1
)

endlocal
