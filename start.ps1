$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = '1'

$VersionFile = Join-Path $PSScriptRoot 'VERSION'
$Version = '0.2.3'
if (Test-Path -LiteralPath $VersionFile) {
    $Version = (Get-Content -LiteralPath $VersionFile -TotalCount 1).Trim()
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
    Write-Host 'pip 证书校验失败，改用 trusted-host 重试……'
    & $PythonExe -m pip --retries 1 --timeout 30 --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org @PipArgs
    if ($LASTEXITCODE -ne 0) {
        throw '依赖安装失败。校园网请换手机热点后重试。'
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
    throw '未找到 Python 3.10–3.12。请从 python.org 安装，并勾选 Add python.exe to PATH。'
}

$status = Get-AppStatus
if ($status -and $status.version -eq $Version) {
    Start-Process ($Address + '?v=' + $Version)
    return
}
if ($status) {
    Write-Host '发现旧版听课搭子，正在替换为新版……'
    Stop-Listener
}

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $python = Find-Python
    Write-Host "使用 Python：$python"
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        throw '创建 Python 环境失败。请安装 Python 3.10–3.12，并勾选 Add python.exe to PATH。'
    }
}

Write-Host '正在安装依赖（首次需要联网，可能要几分钟）……'
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
    Write-Warning '翻译模型暂未安装。打开页面后点黄色条「现在安装中文翻译模型」。校园网请换手机热点。'
}

Write-Host '正在启动听课搭子。看到黄色条就点下载按钮；校园网请换手机热点。'
& $venvPython server.py
