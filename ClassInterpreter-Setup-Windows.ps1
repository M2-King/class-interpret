param([string]$TargetPath = '')

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$script:Version = '0.3.3'
$script:StatePath = Join-Path $env:TEMP ('ClassInterpreter-gui-' + [Guid]::NewGuid().ToString('N') + '.json')
$script:AnimationFrame = 0
$script:WorkerFinished = $false
$script:InstallSucceeded = $false

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Class Interpreter Setup'
$form.Size = New-Object System.Drawing.Size(600, 440)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(11, 14, 17)
$form.ForeColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font('Segoe UI', 10)

$brand = New-Object System.Windows.Forms.Label
$brand.Location = New-Object System.Drawing.Point(38, 28)
$brand.Size = New-Object System.Drawing.Size(500, 30)
$brand.Text = 'CLASS INTERPRETER'
$brand.ForeColor = [System.Drawing.Color]::FromArgb(168, 177, 188)
$brand.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 10)
$form.Controls.Add($brand)

$title = New-Object System.Windows.Forms.Label
$title.Location = New-Object System.Drawing.Point(36, 65)
$title.Size = New-Object System.Drawing.Size(515, 48)
$title.Text = 'Preparing your classroom assistant'
$title.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 22)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Location = New-Object System.Drawing.Point(40, 117)
$subtitle.Size = New-Object System.Drawing.Size(505, 42)
$subtitle.Text = 'Your recordings, downloaded models, and settings will be preserved.'
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(170, 180, 192)
$form.Controls.Add($subtitle)

$card = New-Object System.Windows.Forms.Panel
$card.Location = New-Object System.Drawing.Point(38, 176)
$card.Size = New-Object System.Drawing.Size(508, 150)
$card.BackColor = [System.Drawing.Color]::FromArgb(23, 28, 33)
$form.Controls.Add($card)

$wave = New-Object System.Windows.Forms.Label
$wave.Location = New-Object System.Drawing.Point(24, 21)
$wave.Size = New-Object System.Drawing.Size(72, 35)
$wave.Text = '| ||| ||'
$wave.ForeColor = [System.Drawing.Color]::FromArgb(83, 225, 141)
$wave.Font = New-Object System.Drawing.Font('Consolas', 16, [System.Drawing.FontStyle]::Bold)
$card.Controls.Add($wave)

$status = New-Object System.Windows.Forms.Label
$status.Location = New-Object System.Drawing.Point(104, 19)
$status.Size = New-Object System.Drawing.Size(370, 28)
$status.Text = 'Starting installer'
$status.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 12)
$card.Controls.Add($status)

$detail = New-Object System.Windows.Forms.Label
$detail.Location = New-Object System.Drawing.Point(106, 48)
$detail.Size = New-Object System.Drawing.Size(360, 35)
$detail.Text = 'Please keep this window open.'
$detail.ForeColor = [System.Drawing.Color]::FromArgb(159, 169, 181)
$card.Controls.Add($detail)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(26, 103)
$progress.Size = New-Object System.Drawing.Size(454, 15)
$progress.Minimum = 0
$progress.Maximum = 100
$progress.Style = 'Continuous'
$progress.Value = 2
$card.Controls.Add($progress)

$stage = New-Object System.Windows.Forms.Label
$stage.Location = New-Object System.Drawing.Point(40, 345)
$stage.Size = New-Object System.Drawing.Size(390, 24)
$stage.Text = 'Detecting an existing installation...'
$stage.ForeColor = [System.Drawing.Color]::FromArgb(143, 153, 165)
$form.Controls.Add($stage)

$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Location = New-Object System.Drawing.Point(446, 342)
$closeButton.Size = New-Object System.Drawing.Size(100, 34)
$closeButton.Text = 'Done'
$closeButton.FlatStyle = 'Flat'
$closeButton.BackColor = [System.Drawing.Color]::FromArgb(242, 244, 247)
$closeButton.ForeColor = [System.Drawing.Color]::FromArgb(20, 23, 27)
$closeButton.Visible = $false
$closeButton.Add_Click({ $form.Close() })
$form.Controls.Add($closeButton)

$workerScript = {
    param($StatePath, $RequestedTarget, $Version)
    $ErrorActionPreference = 'Stop'
    $tempRoot = Join-Path $env:TEMP ('ClassInterpreter-install-' + [Guid]::NewGuid().ToString('N'))
    $savedLogFolder = Join-Path $env:LOCALAPPDATA 'ClassInterpreter'
    $setupLog = Join-Path $savedLogFolder 'setup.log'
    New-Item -ItemType Directory -Force -Path $savedLogFolder | Out-Null
    [IO.File]::WriteAllText($setupLog, ('Class Interpreter setup started ' + (Get-Date) + [Environment]::NewLine), (New-Object Text.UTF8Encoding($false)))

    function Set-InstallState {
        param([string]$Phase, [string]$Message, [int]$Progress, [string]$State = 'working')
        $payload = @{ phase = $Phase; message = $Message; progress = $Progress; state = $State } | ConvertTo-Json -Compress
        # A single worker owns this file. Direct writes avoid Windows PowerShell's
        # intermittent "file already exists" collision when Move-Item replaces it.
        $stateStream = New-Object IO.FileStream($StatePath, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
        $stateWriter = New-Object IO.StreamWriter($stateStream, (New-Object Text.UTF8Encoding($false)))
        try { $stateWriter.Write($payload) } finally { $stateWriter.Dispose() }
    }

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Add-Type -AssemblyName System.Net.Http
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
        $zipPath = Join-Path $tempRoot 'ClassInterpreter-windows.zip'
        $extractPath = Join-Path $tempRoot 'package'
        New-Item -ItemType Directory -Force -Path $extractPath | Out-Null

        Set-InstallState 'Downloading application' 'Connecting securely to GitHub...' 5
        $url = 'https://github.com/M2-King/class-interpret/releases/download/v' + $Version + '/ClassInterpreter-windows-' + $Version + '.zip'
        $client = New-Object Net.Http.HttpClient
        $response = $client.GetAsync($url, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
        $response.EnsureSuccessStatusCode() | Out-Null
        $total = [long]$response.Content.Headers.ContentLength
        $input = $response.Content.ReadAsStreamAsync().Result
        $output = [IO.File]::Create($zipPath)
        try {
            $buffer = New-Object byte[] 131072
            $received = [long]0
            while (($count = $input.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $output.Write($buffer, 0, $count)
                $received += $count
                if ($total -gt 0) {
                    $percent = 5 + [int](($received * 30) / $total)
                    $mb = [Math]::Round($received / 1MB, 1)
                    Set-InstallState 'Downloading application' ("Downloaded {0} MB" -f $mb) $percent
                }
            }
        } finally {
            $output.Dispose()
            $input.Dispose()
            $client.Dispose()
        }
        if ((Get-Item -LiteralPath $zipPath).Length -lt 1000000) { throw 'The downloaded application package is incomplete.' }

        Set-InstallState 'Extracting application' 'Unpacking verified application files...' 38
        $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
        try {
            $entries = @($archive.Entries)
            $index = 0
            $rootFull = [IO.Path]::GetFullPath($extractPath + [IO.Path]::DirectorySeparatorChar)
            foreach ($entry in $entries) {
                $index += 1
                $destination = [IO.Path]::GetFullPath((Join-Path $extractPath $entry.FullName))
                if (-not $destination.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe path found in package.' }
                if ($entry.FullName.EndsWith('/')) {
                    New-Item -ItemType Directory -Force -Path $destination | Out-Null
                } else {
                    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
                    [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination, $true)
                }
                if (($index % 15) -eq 0 -and $entries.Count -gt 0) {
                    Set-InstallState 'Extracting application' 'Preparing the local application folder...' (38 + [int](($index * 10) / $entries.Count))
                }
            }
        } finally {
            $archive.Dispose()
        }

        $repair = Get-ChildItem -LiteralPath $extractPath -File -Filter 'repair.ps1' -Recurse | Select-Object -First 1
        if (-not $repair) { throw 'The repair component is missing from the package.' }
        Set-InstallState 'Installing and repairing' 'Preserving your data and checking Python...' 52
        $argumentText = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + $repair.FullName + '" -NoLaunch'
        if ($RequestedTarget) {
            $argumentText += ' -TargetPath "' + $RequestedTarget.Replace('"', '""') + '"'
        } else {
            $defaultPath = Join-Path $env:LOCALAPPDATA ('ClassInterpreter\ClassInterpreter-' + $Version)
            $argumentText += ' -DefaultInstallPath "' + $defaultPath.Replace('"', '""') + '"'
        }
        $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $argumentText -WindowStyle Hidden -Wait -PassThru
        $repairLog = Join-Path $repair.DirectoryName 'INSTALL-OR-REPAIR.log'
        if (Test-Path -LiteralPath $repairLog) {
            Copy-Item -LiteralPath $repairLog -Destination (Join-Path $savedLogFolder 'installer.log') -Force -ErrorAction SilentlyContinue
        }
        if ($process.ExitCode -ne 0) {
            $reason = $null
            if (Test-Path -LiteralPath $repairLog) {
                $reason = @(Get-Content -LiteralPath $repairLog | Where-Object { $_ -match 'FAILED:' } | Select-Object -Last 1)
            }
            if (-not $reason) { $reason = 'Repair process returned exit code ' + $process.ExitCode + '.' }
            throw ([string]$reason -replace '^.*?FAILED:\s*', '')
        }

        $detectedLine = $null
        if (Test-Path -LiteralPath $repairLog) {
            $detectedLine = @(Get-Content -LiteralPath $repairLog | Where-Object { $_ -match 'Detected installation:\s*(.+)$' } | Select-Object -Last 1)
        }
        $detectedMatch = [regex]::Match([string]$detectedLine, 'Detected installation:\s*(.+)$')
        if (-not $detectedMatch.Success) {
            throw 'Repair completed, but the installed application path was not returned.'
        }
        $installedPath = $detectedMatch.Groups[1].Value.Trim()
        if (-not (Test-Path -LiteralPath (Join-Path $installedPath 'Start.bat'))) {
            throw ('Start.bat is missing from the repaired folder: ' + $installedPath)
        }

        $bundledModelFolder = Join-Path $installedPath 'hf\bundled\faster-whisper-small'
        $bundledModel = Join-Path $bundledModelFolder 'model.bin'
        $legacyModel = Join-Path $installedPath 'hf\modelscope\gpustack--faster-whisper-small\model.bin'
        if (-not (Test-Path -LiteralPath $bundledModel) -and -not (Test-Path -LiteralPath $legacyModel)) {
            $modelZip = Join-Path $tempRoot 'ClassInterpreter-Model-Small.zip'
            $modelTarget = Join-Path $installedPath 'hf\bundled'
            New-Item -ItemType Directory -Force -Path $modelTarget | Out-Null
            Set-InstallState 'Downloading speech model' 'Adding the ready-to-use Small offline model...' 57
            $modelUrl = 'https://github.com/M2-King/class-interpret/releases/download/v' + $Version + '/ClassInterpreter-Model-Small.zip'
            $modelClient = New-Object Net.Http.HttpClient
            try {
                $modelResponse = $modelClient.GetAsync($modelUrl, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
                $modelResponse.EnsureSuccessStatusCode() | Out-Null
                $modelTotal = [long]$modelResponse.Content.Headers.ContentLength
                $modelInput = $modelResponse.Content.ReadAsStreamAsync().Result
                $modelOutput = [IO.File]::Create($modelZip)
                try {
                    $modelBuffer = New-Object byte[] 131072
                    $modelReceived = [long]0
                    while (($modelCount = $modelInput.Read($modelBuffer, 0, $modelBuffer.Length)) -gt 0) {
                        $modelOutput.Write($modelBuffer, 0, $modelCount)
                        $modelReceived += $modelCount
                        if ($modelTotal -gt 0) {
                            $modelPercent = 57 + [int](($modelReceived * 28) / $modelTotal)
                            $modelMb = [Math]::Round($modelReceived / 1MB, 1)
                            Set-InstallState 'Downloading speech model' ("Downloaded {0} MB of the offline model" -f $modelMb) $modelPercent
                        }
                    }
                } finally {
                    $modelOutput.Dispose()
                    $modelInput.Dispose()
                }
            } finally {
                $modelClient.Dispose()
            }
            if ((Get-Item -LiteralPath $modelZip).Length -lt 400MB) { throw 'The downloaded Small speech model is incomplete.' }

            Set-InstallState 'Installing speech model' 'Making offline transcription ready...' 86
            if (Test-Path -LiteralPath $bundledModelFolder) {
                Remove-Item -LiteralPath $bundledModelFolder -Recurse -Force
            }
            $modelArchive = [IO.Compression.ZipFile]::OpenRead($modelZip)
            try {
                $modelRootFull = [IO.Path]::GetFullPath($modelTarget + [IO.Path]::DirectorySeparatorChar)
                foreach ($modelEntry in $modelArchive.Entries) {
                    $modelDestination = [IO.Path]::GetFullPath((Join-Path $modelTarget $modelEntry.FullName))
                    if (-not $modelDestination.StartsWith($modelRootFull, [StringComparison]::OrdinalIgnoreCase)) {
                        throw 'Unsafe path found in speech model package.'
                    }
                    if ($modelEntry.FullName.EndsWith('/')) {
                        New-Item -ItemType Directory -Force -Path $modelDestination | Out-Null
                    } else {
                        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $modelDestination) | Out-Null
                        [IO.Compression.ZipFileExtensions]::ExtractToFile($modelEntry, $modelDestination, $true)
                    }
                }
            } finally {
                $modelArchive.Dispose()
            }
            if (-not (Test-Path -LiteralPath $bundledModel) -or (Get-Item -LiteralPath $bundledModel).Length -lt 400MB) {
                throw 'The Small speech model could not be installed correctly.'
            }
        } else {
            Set-InstallState 'Speech model ready' 'Preserved the existing Small offline model.' 86
        }

        try { Invoke-WebRequest -Method POST -Uri 'http://127.0.0.1:8765/api/shutdown' -TimeoutSec 2 -UseBasicParsing | Out-Null } catch { }
        $venvPrefix = [IO.Path]::GetFullPath((Join-Path $installedPath '.venv')).TrimEnd('\') + '\'
        foreach ($oldProcess in @(Get-Process -Name 'python' -ErrorAction SilentlyContinue)) {
            $oldPath = $null
            try { $oldPath = [string]$oldProcess.Path } catch { }
            if ($oldPath -and $oldPath.StartsWith($venvPrefix, [StringComparison]::OrdinalIgnoreCase)) {
                & taskkill.exe /PID $oldProcess.Id /T /F *> $null
            }
        }
        Start-Sleep -Milliseconds 700

        Set-InstallState 'Starting application' 'Preparing Python packages. First launch can take several minutes...' 90
        $startupLog = Join-Path $savedLogFolder 'startup.log'
        $startupErrorLog = Join-Path $savedLogFolder 'startup-error.log'
        Remove-Item -LiteralPath $startupLog, $startupErrorLog -Force -ErrorAction SilentlyContinue
        $starter = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d', '/c', 'Start.bat') -WorkingDirectory $installedPath -WindowStyle Hidden -RedirectStandardOutput $startupLog -RedirectStandardError $startupErrorLog -PassThru
        $ready = $false
        foreach ($attempt in 1..450) {
            try {
                $service = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 2
                if ([string]$service.version -eq $Version) {
                    $ready = $true
                    break
                }
            } catch { }
            if ($starter.HasExited) {
                $startupReason = $null
                if (Test-Path -LiteralPath $startupErrorLog) {
                    $startupReason = @(Get-Content -LiteralPath $startupErrorLog | Where-Object { $_.Trim() } | Select-Object -Last 1)
                }
                if (-not $startupReason -and (Test-Path -LiteralPath $startupLog)) {
                    $startupReason = @(Get-Content -LiteralPath $startupLog | Where-Object { $_.Trim() } | Select-Object -Last 1)
                }
                if (-not $startupReason) { $startupReason = 'The application startup process closed before the local service became ready.' }
                throw ([string]$startupReason)
            }
            $elapsed = $attempt * 2
            $startupProgress = 90 + [Math]::Min(9, [int](($attempt * 9) / 450))
            Set-InstallState 'Starting application' ("Installing packages and starting the local service... {0}s" -f $elapsed) $startupProgress
            Start-Sleep -Seconds 2
        }
        if (-not $ready) { throw 'Startup timed out after 15 minutes. See startup.log in LocalAppData\ClassInterpreter.' }
        Set-InstallState 'Installation complete' 'Class Interpreter is ready and opening in your browser.' 100 'complete'
    } catch {
        $setupFailure = ((Get-Date).ToString('s') + '  FAILED: ' + $_.Exception.Message + [Environment]::NewLine + $_.ScriptStackTrace + [Environment]::NewLine)
        try { [IO.File]::AppendAllText($setupLog, $setupFailure, (New-Object Text.UTF8Encoding($false))) } catch { }
        Set-InstallState 'Installation needs attention' $_.Exception.Message 100 'failed'
    } finally {
        if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

$powershell = [PowerShell]::Create()
[void]$powershell.AddScript($workerScript).AddArgument($script:StatePath).AddArgument($TargetPath).AddArgument($script:Version)
$async = $powershell.BeginInvoke()

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 160
$timer.Add_Tick({
    $script:AnimationFrame = ($script:AnimationFrame + 1) % 4
    $patterns = @('| ||| ||', '|| | |||', '||| || |', '|| ||| |')
    $wave.Text = $patterns[$script:AnimationFrame]
    if (Test-Path -LiteralPath $script:StatePath) {
        try {
            $current = Get-Content -Raw -LiteralPath $script:StatePath | ConvertFrom-Json
            $status.Text = [string]$current.phase
            $detail.Text = [string]$current.message
            $value = [Math]::Max(0, [Math]::Min(100, [int]$current.progress))
            $progress.Value = $value
            $stage.Text = if ($current.state -eq 'working') { 'Installing' + ('.' * (($script:AnimationFrame % 3) + 1)) } else { '' }
            if ($current.state -eq 'complete') {
                $script:InstallSucceeded = $true
                $wave.ForeColor = [System.Drawing.Color]::FromArgb(83, 225, 141)
                $stage.Text = 'Ready to use'
                $closeButton.Visible = $true
            } elseif ($current.state -eq 'failed') {
                $wave.ForeColor = [System.Drawing.Color]::FromArgb(239, 91, 91)
                $progress.ForeColor = [System.Drawing.Color]::FromArgb(239, 91, 91)
                $stage.Text = 'Review the message above, then try again.'
                $closeButton.Text = 'Close'
                $closeButton.Visible = $true
            }
        } catch { }
    }
    if ($async.IsCompleted -and -not $script:WorkerFinished) {
        $script:WorkerFinished = $true
        try { $powershell.EndInvoke($async) } catch { }
        $powershell.Dispose()
    }
})

$form.Add_Shown({ $timer.Start() })
$form.Add_FormClosed({
    $timer.Stop()
    if (-not $script:WorkerFinished) {
        try { $powershell.Stop() } catch { }
        $powershell.Dispose()
    }
    Remove-Item -LiteralPath $script:StatePath, ($script:StatePath + '.new') -Force -ErrorAction SilentlyContinue
})

[void]$form.ShowDialog()
if (-not $script:InstallSucceeded) { exit 1 }
exit 0
