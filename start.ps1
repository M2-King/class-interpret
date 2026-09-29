$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = '1'
$script:LastNativeExit = 0
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

$VersionFile = Join-Path $PSScriptRoot 'VERSION'
$Version = '0.3.1'
if (Test-Path -LiteralPath $VersionFile) {
    $Version = (Get-Content -LiteralPath $VersionFile -TotalCount 1 -Encoding UTF8).Trim()
}
$Address = 'http://127.0.0.1:8765/'
$Port = 8765
$RuntimeDir = Join-Path $PSScriptRoot '.runtime'
$PrivatePython = Join-Path $PSScriptRoot '.runtime\python\python.exe'

if (-not $env:HF_ENDPOINT) { $env:HF_ENDPOINT = 'https://hf-mirror.com' }
if (-not $env:HF_HUB_DOWNLOAD_TIMEOUT) { $env:HF_HUB_DOWNLOAD_TIMEOUT = '180' }
$env:CLASS_INTERPRET_HF = Join-Path $PSScriptRoot 'hf'
$env:CLASS_INTERPRET_DATA = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Force -Path $env:CLASS_INTERPRET_HF, $env:CLASS_INTERPRET_DATA, $RuntimeDir | Out-Null

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

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList
    )
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if ($ArgumentList -and $ArgumentList.Count -gt 0) {
        & $FilePath @ArgumentList | ForEach-Object { Write-Host $_ }
    } else {
        & $FilePath | ForEach-Object { Write-Host $_ }
    }
    $script:LastNativeExit = $LASTEXITCODE
    $ErrorActionPreference = $saved
    if ($null -eq $script:LastNativeExit) { $script:LastNativeExit = 0 }
}

function Invoke-NativeText {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList
    )
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $text = & $FilePath @ArgumentList 2>$null | Out-String
    $script:LastNativeExit = $LASTEXITCODE
    $ErrorActionPreference = $saved
    if ($null -eq $script:LastNativeExit) { $script:LastNativeExit = 0 }
    return ([string]$text).Trim()
}

function Save-Url {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$OutFile
    )
    foreach ($old in @($OutFile, ($OutFile + '.part'))) {
        if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue }
    }
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        foreach ($extra in @('', '--ssl-no-revoke')) {
            $curlArgs = @('-sS', '-fL', '--retry', '2', '--connect-timeout', '20', '-o', $OutFile)
            if ($extra) { $curlArgs += $extra }
            $curlArgs += $Url
            Invoke-Native -FilePath 'curl.exe' -ArgumentList $curlArgs
            if (($script:LastNativeExit -eq 0) -and (Test-Path -LiteralPath $OutFile) -and ((Get-Item -LiteralPath $OutFile).Length -gt 1000000)) {
                return $true
            }
        }
    }
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -TimeoutSec 180
    } catch { }
    $ErrorActionPreference = $saved
    if ((Test-Path -LiteralPath $OutFile) -and ((Get-Item -LiteralPath $OutFile).Length -gt 1000000)) {
        return $true
    }
    return $false
}

function Test-PythonExe {
    param(
        [string]$Exe,
        [switch]$NeedVenv
    )
    if (-not $Exe) { return $false }
    if ($Exe -match 'WindowsApps') { return $false }
    if (-not (Test-Path -LiteralPath $Exe)) { return $false }
    try {
        if ((Get-Item -LiteralPath $Exe).Length -lt 4096) { return $false }
    } catch { return $false }
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if ($NeedVenv) {
        Invoke-Native -FilePath $Exe -ArgumentList @('-c', 'import sys, venv; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)')
    } else {
        Invoke-Native -FilePath $Exe -ArgumentList @('-c', 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)')
    }
    $ok = ($script:LastNativeExit -eq 0)
    $ErrorActionPreference = $saved
    return $ok
}

function ConvertTo-PythonPath {
    param($Value)
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($item in @($Value)) {
        if ($null -eq $item) { continue }
        $parts.Add([string]$item)
    }
    $blob = [string]::Join("`n", $parts.ToArray())
    $regex = '(?i)((?:[A-Za-z]:\\|\\\\)[^:*?"<>|\r\n]*python\.exe)'
    $match = [regex]::Match($blob, $regex)
    if ($match.Success) { return $match.Groups[1].Value.Trim() }
    if (Test-Path -LiteralPath $PrivatePython) { return $PrivatePython }
    return $null
}

function Find-Python {
    param([switch]$NeedVenv)
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $candidates = @()

    $pyCmd = $null
    $pyWhere = Get-Command py -ErrorAction SilentlyContinue
    if ($pyWhere -and $pyWhere.Source -and ($pyWhere.Source -notmatch 'WindowsApps')) {
        $pyCmd = $pyWhere.Source
    } elseif (Test-Path -LiteralPath (Join-Path $env:SystemRoot 'py.exe')) {
        $pyCmd = Join-Path $env:SystemRoot 'py.exe'
    } elseif (Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe')) {
        $pyCmd = Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe'
    }
    if ($pyCmd) {
        foreach ($item in @('-3.12', '-3.11', '-3.10', '-3')) {
            $exe = Invoke-NativeText -FilePath $pyCmd -ArgumentList @($item, '-c', 'import sys; print(sys.executable)')
            if ($script:LastNativeExit -eq 0 -and $exe) { $candidates += $exe }
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and $pythonCmd.Source -and ($pythonCmd.Source -notmatch 'WindowsApps')) {
        $exe = Invoke-NativeText -FilePath 'python' -ArgumentList @('-c', 'import sys; print(sys.executable)')
        if ($script:LastNativeExit -eq 0 -and $exe) { $candidates += $exe }
    }

    $folders = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
        (Join-Path $env:ProgramFiles 'Python312\python.exe'),
        (Join-Path $env:ProgramFiles 'Python311\python.exe'),
        (Join-Path $env:ProgramFiles 'Python310\python.exe'),
        (Join-Path $env:ProgramFiles 'Python\python.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\python.exe'),
        (Join-Path $env:USERPROFILE 'miniconda3\python.exe'),
        (Join-Path $env:USERPROFILE 'miniforge3\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'anaconda3\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'miniconda3\python.exe')
    )
    if (${env:ProgramFiles(x86)}) {
        $folders += Join-Path ${env:ProgramFiles(x86)} 'Python312\python.exe'
        $folders += Join-Path ${env:ProgramFiles(x86)} 'Python311\python.exe'
        $folders += Join-Path ${env:ProgramFiles(x86)} 'Python310\python.exe'
    }
    $candidates += $folders

    foreach ($root in @(
            'HKCU:\Software\Python\PythonCore',
            'HKLM:\Software\Python\PythonCore',
            'HKLM:\Software\Wow6432Node\Python\PythonCore'
        )) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue | ForEach-Object {
            $ip = Join-Path $_.PSPath 'InstallPath'
            if (Test-Path -LiteralPath $ip) {
                $dir = $null
                try {
                    $dir = (Get-Item -LiteralPath $ip).GetValue('')
                } catch { }
                if ($dir) { $candidates += (Join-Path $dir 'python.exe') }
            }
        }
    }

    $candidates += $PrivatePython

    $ErrorActionPreference = $saved
    $seen = @{}
    foreach ($exe in $candidates) {
        if (-not $exe) { continue }
        $key = $exe.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        if (Test-PythonExe -Exe $exe -NeedVenv:$NeedVenv) { return $exe }
        if ((-not $NeedVenv) -and (Test-PythonExe -Exe $exe)) { return $exe }
    }
    return $null
}

function Enable-EmbeddableSite {
    param([string]$Dest)
    if (-not (Test-Path -LiteralPath $Dest)) { return }
    $zip = Get-ChildItem -LiteralPath $Dest -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'python*.zip' } | Select-Object -First 1
    $zipName = 'python312.zip'
    if ($zip) { $zipName = $zip.Name }
    $pth = Get-ChildItem -LiteralPath $Dest -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'python*._pth' -or $_.Extension -eq '.pth' } | Select-Object -First 1
    $pthPath = Join-Path $Dest 'python312._pth'
    if ($pth) { $pthPath = $pth.FullName }
    $content = $zipName + "`r`n.`r`nLib\site-packages`r`nimport site`r`n"
    [IO.File]::WriteAllText($pthPath, $content)
    Write-Host ("Wrote " + $pthPath + " so pip can be imported")
}

function Test-PipModule {
    param([string]$Exe)
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    Invoke-Native -FilePath $Exe -ArgumentList @('-m', 'pip', '--version')
    return ($script:LastNativeExit -eq 0)
}

function Ensure-LocalPip {
    param([string]$Exe)
    if (-not $Exe) { $Exe = $PrivatePython }
    if (-not (Test-Path -LiteralPath $Exe)) { return }
    $dest = Split-Path -Parent $Exe
    Enable-EmbeddableSite -Dest $dest
    if (Test-PipModule -Exe $Exe) { return }
    Write-Host 'pip module missing; installing get-pip.py...'
    $getPip = Join-Path $RuntimeDir 'get-pip.py'
    $pipUrls = @(
        'https://bootstrap.pypa.io/get-pip.py',
        'https://mirrors.aliyun.com/pypi/get-pip.py'
    )
    foreach ($url in $pipUrls) {
        $saved = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            Invoke-WebRequest -Uri $url -OutFile $getPip -UseBasicParsing -TimeoutSec 60
        } catch { }
        $ErrorActionPreference = $saved
        if ((Test-Path -LiteralPath $getPip) -and ((Get-Item -LiteralPath $getPip).Length -gt 10000)) { break }
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            Invoke-Native -FilePath 'curl.exe' -ArgumentList @('-sS', '-fL', '--retry', '2', '-o', $getPip, $url)
            if ((Test-Path -LiteralPath $getPip) -and ((Get-Item -LiteralPath $getPip).Length -gt 10000)) { break }
        }
    }
    if (Test-Path -LiteralPath $getPip) {
        Invoke-Native -FilePath $Exe -ArgumentList @($getPip, '--no-warn-script-location')
    }
    Enable-EmbeddableSite -Dest $dest
    if (Test-PipModule -Exe $Exe) { return }
    Write-Host 'pip still missing after get-pip. Check python*._pth has import site.'
}

function Install-EmbeddablePython {
    $dest = Join-Path $RuntimeDir 'python'
    $arch = 'amd64'
    if (-not [Environment]::Is64BitOperatingSystem) { $arch = 'win32' }
    $zipName = "python-3.12.10-embed-$arch.zip"
    $zipPath = Join-Path $RuntimeDir $zipName
    $urls = @(
        ("https://mirrors.huaweicloud.com/python/3.12.10/" + $zipName),
        ("https://cdn.npmmirror.com/binaries/python/3.12.10/" + $zipName),
        ("https://www.python.org/ftp/python/3.12.10/" + $zipName)
    )
    Write-Host 'Downloading embed-amd64 Python 3.12 (no admin)...'
    $got = $false
    foreach ($url in $urls) {
        Write-Host ("Trying " + $url)
        if (Save-Url -Url $url -OutFile $zipPath) { $got = $true; break }
    }
    if (-not $got) { return }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $dest -Force | Out-Null
    Ensure-LocalPip -Exe $PrivatePython
}

function Install-PrivatePython {
    if (Test-PythonExe -Exe $PrivatePython) { return }
    $dest = Join-Path $RuntimeDir 'python'
    $arch = 'amd64'
    $file = 'python-3.12.10-amd64.exe'
    if (-not [Environment]::Is64BitOperatingSystem) {
        $arch = 'win32'
        $file = 'python-3.12.10.exe'
    }
    $setup = Join-Path $RuntimeDir $file
    $urls = @(
        ("https://mirrors.huaweicloud.com/python/3.12.10/" + $file),
        ("https://cdn.npmmirror.com/binaries/python/3.12.10/" + $file),
        ("https://www.python.org/ftp/python/3.12.10/" + $file)
    )
    Write-Host 'Downloading official Python 3.12 into this folder (about 26 MB, no admin)...'
    $got = $false
    foreach ($url in $urls) {
        Write-Host ("Trying " + $url)
        if (Save-Url -Url $url -OutFile $setup) { $got = $true; break }
    }
    if ($got) {
        Unblock-File -LiteralPath $setup -ErrorAction SilentlyContinue
        Write-Host 'Installing Python 3.12 next to Start.bat...'
        $argList = @(
            '/quiet',
            'InstallAllUsers=0',
            'PrependPath=0',
            'Include_launcher=0',
            'Include_test=0',
            'Include_doc=0',
            'Include_pip=1',
            'Shortcuts=0',
            'AssociateFiles=0',
            'SimpleInstall=1',
            ('TargetDir="' + $dest + '"')
        )
        try {
            $proc = Start-Process -FilePath $setup -ArgumentList $argList -Wait -PassThru
            if ($proc -and $proc.ExitCode -ne 0) {
                Write-Host ("Installer exit code " + $proc.ExitCode)
            }
        } catch {
            Write-Host 'Quiet installer could not run. Trying the embeddable zip...'
        }
    }
    if (-not (Test-PythonExe -Exe $PrivatePython)) {
        Install-EmbeddablePython
    }
}

function Ensure-Python {
    $found = ConvertTo-PythonPath (Find-Python)
    if ($found) { return $found }
    Write-Host 'Python 3.10-3.12 not found on PATH. This is OK; downloading a private copy...'
    $null = Install-PrivatePython
    $found = ConvertTo-PythonPath (Find-Python)
    if ($found) { return $found }
    try { Start-Process 'https://www.python.org/downloads/windows/' } catch { }
    throw 'Could not install Python 3.12. Switch to a phone hotspot and double-click Start.bat again. Or install Python 3.12 from python.org and check Add python.exe to PATH.'
}

function Install-WithPip {
    param(
        [Parameter(Mandatory = $true)]$PythonExe,
        [Parameter(Mandatory = $true)][string[]]$PipArgs
    )
    $exe = ConvertTo-PythonPath $PythonExe
    if (-not $exe) { throw 'Python path missing after install. Double-click Start.bat again.' }
    Ensure-LocalPip -Exe $exe
    if (-not (Test-PipModule -Exe $exe)) {
        throw 'pip is not available in the local Python. Delete the .runtime folder and double-click Start.bat again.'
    }
    Write-Host ("pip using " + $exe)
    $pipArgs = @('-m', 'pip', '--retries', '1', '--timeout', '30') + $PipArgs
    Invoke-Native -FilePath $exe -ArgumentList $pipArgs
    if ($script:LastNativeExit -eq 0) { return }
    Write-Host 'pip SSL failed, retrying with trusted-host...'
    $pipArgs = @('-m', 'pip', '--retries', '1', '--timeout', '30', '--trusted-host', 'pypi.org', '--trusted-host', 'files.pythonhosted.org', '--trusted-host', 'pypi.python.org') + $PipArgs
    Invoke-Native -FilePath $exe -ArgumentList $pipArgs
    if ($script:LastNativeExit -ne 0) {
        throw 'pip install failed. Switch to a phone hotspot and try again.'
    }
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
    $python = ConvertTo-PythonPath (Ensure-Python)
    if (-not $python) { throw 'Python 3.12 was downloaded but the exe path was not found. Double-click Start.bat again.' }
    Write-Host ("Using Python: " + $python)
    $hasVenv = Test-PythonExe -Exe $python -NeedVenv
    if ($hasVenv) {
        Invoke-Native -FilePath $python -ArgumentList @('-m', 'venv', '.venv')
        if ($script:LastNativeExit -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
            Write-Host 'venv create failed; installing packages into the local Python instead.'
            $venvPython = $python
        }
    } else {
        Write-Host 'This Python has no venv module; installing packages into the local runtime.'
        $venvPython = $python
    }
}
$venvPython = ConvertTo-PythonPath $venvPython
if (-not $venvPython) { throw 'Python exe missing. Delete this folder and unzip ClassInterpreter-windows-0.3.1.zip again.' }

Write-Host 'Installing packages (first run needs internet, a few minutes)...'
Install-WithPip -PythonExe $venvPython -PipArgs @('install', '--upgrade', 'pip')
Install-WithPip -PythonExe $venvPython -PipArgs @('install', 'certifi')
$cert = Invoke-NativeText -FilePath $venvPython -ArgumentList @('-c', 'import certifi; print(certifi.where())')
if ($script:LastNativeExit -eq 0 -and $cert) {
    $env:SSL_CERT_FILE = $cert
    $env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
    $env:CURL_CA_BUNDLE = $env:SSL_CERT_FILE
}
Install-WithPip -PythonExe $venvPython -PipArgs @('install', '-r', 'requirements.txt')
Invoke-Native -FilePath $venvPython -ArgumentList @('setup_models.py')
if ($script:LastNativeExit -ne 0) {
    Write-Warning 'Translation model not installed yet. Use the yellow button in the webpage. If campus Wi-Fi fails, use a phone hotspot.'
}

Write-Host 'Starting. In the webpage, use the yellow buttons to download models. Use a phone hotspot on campus Wi-Fi.'
Invoke-Native -FilePath $venvPython -ArgumentList @('server.py')
