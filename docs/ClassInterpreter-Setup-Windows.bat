@echo off
setlocal EnableExtensions
set "SETUP_SCRIPT=%TEMP%\ClassInterpreter-gui-%RANDOM%-%RANDOM%.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -TimeoutSec 120 -Uri 'https://github.com/M2-King/class-interpret/releases/download/v0.3.3/ClassInterpreter-Setup-Windows.ps1' -OutFile '%SETUP_SCRIPT%'"
if errorlevel 1 goto :FAILED
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SETUP_SCRIPT%"
set "RC=%ERRORLEVEL%"
del /q "%SETUP_SCRIPT%" >nul 2>&1
if not "%RC%"=="0" goto :FAILED
exit /b 0

:FAILED
echo.
echo Setup failed. Check the internet connection and run this installer again.
pause
exit /b 1
