@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Class Interpreter 0.3.3 - Download and Repair
echo Target: %CD%
echo.
if not exist "%~dp0fix.ps1" (
  echo fix.ps1 is missing. Please download the standalone installer again.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix.ps1" -TargetPath "%~dp0"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
