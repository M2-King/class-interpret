param(
    [string]$TargetPath = '',
    [string]$DefaultInstallPath = '',
    [switch]$QuietLaunch,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$Version = '0.3.3'
$LogPath = Join-Path $PSScriptRoot 'INSTALL-OR-REPAIR.log'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

function Write-RepairLog {
    param([string]$Message)
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
    Write-Host $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Test-AppFolder {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    return ((Test-Path -LiteralPath (Join-Path $Path 'server.py')) -or
            (Test-Path -LiteralPath (Join-Path $Path 'Start.bat')))
}

function Test-Python {
    param([string]$Exe)
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe -PathType Leaf)) { return $false }
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" *> $null
        $ok = ($LASTEXITCODE -eq 0)
    } catch {
        $ok = $false
    }
    $ErrorActionPreference = $oldPreference
    return $ok
}

function Stop-AppForRepair {
    param([string]$VenvPath)
    try {
        Invoke-WebRequest -Method POST -Uri 'http://127.0.0.1:8765/api/shutdown' -TimeoutSec 2 -UseBasicParsing | Out-Null
        Start-Sleep -Milliseconds 800
    } catch { }
    try {
        $prefix = [IO.Path]::GetFullPath($VenvPath).TrimEnd('\') + '\'
        foreach ($process in @(Get-Process -ErrorAction SilentlyContinue)) {
            $processPath = $null
            try { $processPath = [string]$process.Path } catch { }
            if ($processPath -and $processPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 500
    } catch { }
}

function Add-AppCandidate {
    param([string]$Path, [hashtable]$Table)
    if (-not (Test-AppFolder -Path $Path)) { return }
    try { $full = (Resolve-Path -LiteralPath $Path).Path.TrimEnd('\') } catch { return }
    if ($full -match '(?i)\\\.worktrees\\|\\\.git\\') { return }
    if ((Split-Path -Leaf $full) -notlike 'ClassInterpreter-*') { return }
    $Table[$full.ToLowerInvariant()] = $full
}

function Find-AppFolders {
    param([string[]]$Roots)
    $found = @{}
    $skipNames = @('$Recycle.Bin', 'Windows', 'Program Files', 'Program Files (x86)',
                   'ProgramData', 'System Volume Information', 'Recovery', '.git', '.worktrees',
                   'node_modules', '.runtime', '.venv')
    foreach ($root in ($Roots | Select-Object -Unique)) {
        if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        Add-AppCandidate -Path $root -Table $found
        $queue = New-Object System.Collections.Queue
        $queue.Enqueue(@($root, 0))
        $visited = 0
        while ($queue.Count -gt 0 -and $visited -lt 1200) {
            $item = $queue.Dequeue()
            $folder = [string]$item[0]
            $depth = [int]$item[1]
            $visited += 1
            if ($depth -ge 3) { continue }
            $children = @(Get-ChildItem -LiteralPath $folder -Directory -Force -ErrorAction SilentlyContinue)
            foreach ($child in $children) {
                if ($skipNames -contains $child.Name) { continue }
                if ($child.FullName -match '(?i)\\\.worktrees\\|\\\.git\\') { continue }
                if ($child.Name -like 'ClassInterpreter-*') {
                    Add-AppCandidate -Path $child.FullName -Table $found
                }
                $queue.Enqueue(@($child.FullName, ($depth + 1)))
            }
        }
    }
    return @($found.Values)
}

function Get-CandidateScore {
    param([string]$Path, [string]$SourcePath)
    $score = 0
    if ($Path -eq $SourcePath) { $score -= 10000 }
    if (Test-Path -LiteralPath (Join-Path $Path '.venv')) { $score += 1000 }
    if (Test-Path -LiteralPath (Join-Path $Path 'data')) { $score += 300 }
    if (Test-Path -LiteralPath (Join-Path $Path 'hf')) { $score += 200 }
    if ((Split-Path -Leaf $Path) -eq ('ClassInterpreter-' + $Version)) { $score += 100 }
    try { $score += [int][Math]::Min(99, ((Get-Item -LiteralPath $Path).LastWriteTimeUtc.Ticks / 10000000000000000)) } catch { }
    return $score
}

function Copy-RecoveryFile {
    param([string]$RelativePath, [string]$SourcePath, [string]$DestinationPath, [string]$BackupPath)
    $sourceFile = Join-Path $SourcePath $RelativePath
    if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) { return }
    $destinationFile = Join-Path $DestinationPath $RelativePath
    $destinationParent = Split-Path -Parent $destinationFile
    New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    $different = $true
    if (Test-Path -LiteralPath $destinationFile -PathType Leaf) {
        try { $different = ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceFile).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationFile).Hash) } catch { }
    }
    if (-not $different) { return }
    if (Test-Path -LiteralPath $destinationFile -PathType Leaf) {
        $backupFile = Join-Path $BackupPath $RelativePath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupFile) | Out-Null
        Copy-Item -LiteralPath $destinationFile -Destination $backupFile -Force
    }
    Copy-Item -LiteralPath $sourceFile -Destination $destinationFile -Force
    Write-RepairLog ('Recovered: ' + $RelativePath)
}

try {
    Set-Content -LiteralPath $LogPath -Value ('Class Interpreter repair started ' + (Get-Date)) -Encoding UTF8

    $source = Join-Path $PSScriptRoot ('ClassInterpreter-' + $Version)
    if (-not (Test-AppFolder -Path $source)) {
        $source = @(Get-ChildItem -LiteralPath $PSScriptRoot -Directory -Filter ('ClassInterpreter-*' + $Version) -ErrorAction SilentlyContinue |
            Where-Object { Test-AppFolder -Path $_.FullName } |
            Select-Object -First 1 -ExpandProperty FullName)
    }
    if ((-not (Test-AppFolder -Path $source)) -or -not (Test-Path -LiteralPath (Join-Path $source 'server.py'))) {
        throw 'The clean application folder is missing. Extract the complete Windows zip first.'
    }
    $source = (Resolve-Path -LiteralPath $source).Path.TrimEnd('\')
    Write-RepairLog ('Clean package: ' + $source)

    if ($TargetPath) {
        $target = [IO.Path]::GetFullPath($TargetPath).TrimEnd('\')
        if ((Test-Path -LiteralPath $target) -and -not (Test-Path -LiteralPath $target -PathType Container)) {
            throw ('The selected install path is not a folder: ' + $target)
        }
        New-Item -ItemType Directory -Force -Path $target | Out-Null
    } else {
        $roots = @($PSScriptRoot, (Split-Path -Parent $PSScriptRoot), $env:USERPROFILE,
                   (Join-Path $env:USERPROFILE 'Desktop'), (Join-Path $env:USERPROFILE 'Downloads'),
                   (Join-Path $env:USERPROFILE 'Documents'))
        $roots += @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object { $_.Root })
        $candidates = @(Find-AppFolders -Roots $roots)
        $target = @($candidates | Sort-Object -Property @{ Expression = { Get-CandidateScore -Path $_ -SourcePath $source }; Descending = $true } | Select-Object -First 1)
        if (-not $target -or (Get-CandidateScore -Path $target -SourcePath $source) -lt 0) {
            if ($DefaultInstallPath) {
                $target = [IO.Path]::GetFullPath($DefaultInstallPath).TrimEnd('\')
                New-Item -ItemType Directory -Force -Path $target | Out-Null
            } else {
                $target = $source
            }
        }
    }
    Write-RepairLog ('Detected installation: ' + $target)

    $backup = Join-Path $target ('.repair-backup\' + $Stamp)
    $files = @('Start.bat', 'start.ps1', 'win_bootstrap.py', 'server.py', 'setup_models.py',
               'setup_whisper.py', 'setup_deepseek.py', 'ssl_certs.py', 'whisper_hub.py',
               'deepseek_hub.py', 'deepseek_api.py', 'secret_box.py', 'requirements.txt',
               'index.html', 'app.js', 'style.css', 'VERSION', 'README.md', 'pip.pyz',
               'get-pip.py', 'deepseek_api.enc', 'HOW-TO-START.txt')
    $extraBatch = @(Get-ChildItem -LiteralPath $source -File -Filter '*.bat' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne 'Start.bat' } | Select-Object -ExpandProperty Name)
    $files += $extraBatch
    foreach ($file in ($files | Select-Object -Unique)) {
        if ($target -ne $source) { Copy-RecoveryFile -RelativePath $file -SourcePath $source -DestinationPath $target -BackupPath $backup }
    }

    $targetRuntime = Join-Path $target '.runtime\python\python.exe'
    if (-not (Test-Python -Exe $targetRuntime)) {
        $sourceRuntime = Join-Path $source '.runtime\python\python.exe'
        if (-not (Test-Python -Exe $sourceRuntime)) { throw 'Bundled Python is missing or damaged in the downloaded package.' }
        $runtimeFolder = Join-Path $target '.runtime'
        if (Test-Path -LiteralPath $runtimeFolder) {
            $runtimeBackup = Join-Path $backup '.runtime'
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtimeBackup) | Out-Null
            Move-Item -LiteralPath $runtimeFolder -Destination $runtimeBackup -Force
        }
        Copy-Item -LiteralPath (Join-Path $source '.runtime') -Destination $runtimeFolder -Recurse -Force
        Write-RepairLog 'Recovered bundled Python runtime.'
    }

    $venv = Join-Path $target '.venv'
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    if ((Test-Path -LiteralPath $venv) -and -not (Test-Python -Exe $venvPython)) {
        Write-RepairLog 'Closing the old application before rebuilding Python...'
        Stop-AppForRepair -VenvPath $venv
        $quarantine = Join-Path $target ('.venv-broken-' + $Stamp)
        if (Test-Path -LiteralPath $quarantine) {
            $quarantine += '-' + [Guid]::NewGuid().ToString('N').Substring(0, 6)
        }
        $moveError = $null
        foreach ($attempt in 1..3) {
            try {
                Move-Item -LiteralPath $venv -Destination $quarantine -ErrorAction Stop
                $moveError = $null
                break
            } catch {
                $moveError = $_.Exception.Message
                Start-Sleep -Seconds 1
            }
        }
        if (Test-Path -LiteralPath $venv) {
            throw ('Could not preserve the broken .venv. Close every Class Interpreter or Python window and retry. ' + $moveError)
        }
        Write-RepairLog ('Quarantined broken environment: ' + $quarantine)
    }

    Write-RepairLog 'Repair checks completed. Recordings, models, and settings were preserved.'
    if (-not $NoLaunch) {
        Write-RepairLog 'Starting Class Interpreter...'
        if ($QuietLaunch) {
            Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', 'Start.bat') -WorkingDirectory $target -WindowStyle Hidden
        } else {
            Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', 'Start.bat') -WorkingDirectory $target
        }
    }
    exit 0
} catch {
    Write-RepairLog ('FAILED: ' + $_.Exception.Message)
    Write-Host ''
    Write-Host 'Repair failed. The original files were preserved in .repair-backup when possible.'
    exit 1
}
