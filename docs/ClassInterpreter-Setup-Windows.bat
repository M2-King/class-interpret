@echo off
setlocal EnableExtensions
set "SETUP_SCRIPT=%TEMP%\ClassInterpreter-gui-%RANDOM%-%RANDOM%.ps1"
start "" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ErrorActionPreference='Stop'; try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -TimeoutSec 120 -Uri 'https://github.com/M2-King/class-interpret/releases/download/v0.3.3/ClassInterpreter-Setup-Windows.ps1' -OutFile '%SETUP_SCRIPT%'; & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File '%SETUP_SCRIPT%'; if ($LASTEXITCODE -ne 0) { throw 'Installer closed before completion.' } } catch { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Class Interpreter Setup') } finally { Remove-Item -LiteralPath '%SETUP_SCRIPT%' -Force -ErrorAction SilentlyContinue }"
exit /b 0
