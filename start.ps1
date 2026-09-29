$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = '1'

$VersionFile = Join-Path $PSScriptRoot 'VERSION'
$Version = '0.2.5'
if (Test-Path -LiteralPath $VersionFile) {
    $Version = (Get-Content -LiteralPath $VersionFile -TotalCount 1 -Encoding UTF8).Trim()
}
$Address = 'http://127.0.0.1:8765/'
$Port = 8765

if (-not $env:HF_ENDPOINT) { $env:HF_ENDPOINT = 'https://hf-mirror.com' }
if (-not $env:HF_HUB_DOWNLOAD_TIMEOUT) { $env:HF_HUB_DOWNLOAD_TIMEOUT = '180' }
$env:CLASS_INTERPRET_HF = Join-Path $PSScriptRoot 'hf'
$env:CLASS_INTERPRET_DATA = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Force -Path $env:CLASS_INTERPRET_HF, $env:CLASS_INTERPRET_DATA | Out-Null

function Get-AppStatus {
    try {
        return Invoke-RestMethod -Uri ($Address + 'api/status') -TimeoutSec 2
    } catch {
        return $null
    }
}

function Stop-Listener {
    try {
        Invoke-WebRequest -Method POST -Uri ($Address + 'api/shutdown') -TimeoutSec 2 -UseBasicParsing | Out-Null
        Start-Sleep -Seconds 1
    } catch { }
    $pids = @()
    try {
        $pids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        netstat -ano | ForEach-Object {
            if ($_ -match ":$Port\s+\S+\s+\S+\s+LISTENING\s+(\d+)") { $pids += [int]$Matches[1] }
        }
    }
    foreach ($processId in ($pids | Select-Object -Unique)) {
        if ($processId -and $processId -ne 0) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Install-WithPip {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string[]]$PipArgs
    )
    & $PythonExe -m pip --retries 1 --timeout 30 @PipArgs
    if ($LASTEXITCODE -eq 0) { return }
    Write-Host 'pip SSL failed, retrying with trusted-host...'
    & $PythonExe -m pip --retries 1 --timeout 30 --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org @PipArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'pip install failed. Switch to a phone hotspot and try again.'
    }
}

function Find-Python {
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($item in @('3.12', '3.11', '3.10')) {
            $exe = & py "-$item" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { $candidates += $exe.Trim() }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $exe = & python -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { $candidates += $exe.Trim() }
    }
    $ErrorActionPreference = $saved
    foreach ($exe in $candidates) {
        if (-not $exe) { continue }
        & $exe -c 'import sys, venv; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $exe }
    }
    throw 'Python 3.10-3.12 not found. Install it from python.org and check Add python.exe to PATH.'
}

$status = Get-AppStatus
if ($status -and $status.version -eq $Version) {
    Start-Process ($Address + '?v=' + $Version)
    return
}
if ($status) {
    Write-Host 'Old Class Interpreter is running. Replacing it...'
    Stop-Listener
}

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $python = Find-Python
    Write-Host ("Using Python: " + $python)
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        throw 'Failed to create .venv. Install Python 3.10-3.12 and check Add python.exe to PATH.'
    }
}

Write-Host 'Installing packages (first run needs internet, a few minutes)...'
Install-WithPip -PythonExe $venvPython -PipArgs @('install', '--upgrade', 'pip')
Install-WithPip -PythonExe $venvPython -PipArgs @('install', 'certifi')
$cert = & $venvPython -c 'import certifi; print(certifi.where())'
if ($LASTEXITCODE -eq 0 -and $cert) {
    $env:SSL_CERT_FILE = $cert.Trim()
    $env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
    $env:CURL_CA_BUNDLE = $env:SSL_CERT_FILE
}
Install-WithPip -PythonExe $venvPython -PipArgs @('install', '-r', 'requirements.txt')
& $venvPython setup_models.py
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'Translation model not installed yet. Use the yellow button in the webpage. If campus Wi-Fi fails, use a phone hotspot.'
}

Write-Host 'Starting. In the webpage, use the yellow buttons to download models. Use a phone hotspot on campus Wi-Fi.'
& $venvPython server.py
