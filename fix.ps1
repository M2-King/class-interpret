param(
    [string]$TargetPath = '',
    [switch]$InstallMode
)

$ErrorActionPreference = 'Stop'
$Version = '0.3.3'
$PackageUrl = 'https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-windows-0.3.3.zip'
$TempRoot = Join-Path $env:TEMP ('ClassInterpreter-setup-' + [Guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $TempRoot 'ClassInterpreter-windows.zip'
$ExtractPath = Join-Path $TempRoot 'package'

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    New-Item -ItemType Directory -Force -Path $ExtractPath | Out-Null
    Write-Host 'Downloading Class Interpreter 0.3.3...'
    Invoke-WebRequest -Uri $PackageUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 300
    if ((Get-Item -LiteralPath $ZipPath).Length -lt 1000000) { throw 'The downloaded package is incomplete.' }
    Write-Host 'Extracting the application...'
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractPath -Force
    $repair = Get-ChildItem -LiteralPath $ExtractPath -File -Filter 'repair.ps1' -Recurse | Select-Object -First 1
    if (-not $repair) { throw 'The downloaded package does not contain the repair tool.' }
    if ($TargetPath) {
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $repair.FullName -TargetPath $TargetPath
    } elseif ($InstallMode) {
        $defaultPath = Join-Path $env:LOCALAPPDATA ('ClassInterpreter\ClassInterpreter-' + $Version)
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $repair.FullName -DefaultInstallPath $defaultPath
    } else {
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $repair.FullName
    }
    if ($LASTEXITCODE -ne 0) { throw ('Repair returned exit code ' + $LASTEXITCODE) }
    Write-Host 'Installation or repair completed.'
    exit 0
} catch {
    Write-Host ''
    Write-Host ('Installation failed: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Check the internet connection, then run this file again.'
    exit 1
} finally {
    if (Test-Path -LiteralPath $TempRoot) { Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
