$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$address = 'http://127.0.0.1:8765/'
try {
    $running = Invoke-RestMethod -Uri ($address + 'api/status') -TimeoutSec 1
    if ($null -ne $running.translation) { Start-Process $address; return }
} catch { }
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($python) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw '创建 Python 环境失败。请安装 Python 3.10–3.12。' }
}
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败，请检查网络后重试。' }
& $venvPython setup_models.py
if ($LASTEXITCODE -ne 0) { Write-Warning '翻译模型暂未安装；识别仍可使用，安装模型后会显示中文译文。' }
& $venvPython server.py
