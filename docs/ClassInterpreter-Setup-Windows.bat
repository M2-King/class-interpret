@echo off
setlocal EnableExtensions
echo Class Interpreter 0.3.3 - Windows Setup
echo This installer downloads, extracts, repairs, and starts the application.
echo.
set "SETUP_SCRIPT=%TEMP%\ClassInterpreter-setup-%RANDOM%-%RANDOM%.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -TimeoutSec 120 -Uri 'https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/fix.ps1' -OutFile '%SETUP_SCRIPT%'"
if errorlevel 1 goto :FAILED
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%" -InstallMode
set "RC=%ERRORLEVEL%"
del /q "%SETUP_SCRIPT%" >nul 2>&1
if not "%RC%"=="0" goto :FAILED
echo.
echo Setup completed. Class Interpreter is starting.
timeout /t 3 >nul
exit /b 0

:FAILED
echo.
echo Setup failed. Check the internet connection and run this installer again.
pause
exit /b 1
