$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$helpers = Join-Path $root "scripts\RuntimeHelpers.ps1"
$runtime = Join-Path $root ".runtime"
$logs = Join-Path $runtime "logs"
$apiPidFile = Join-Path $runtime "api.pid"
$webPidFile = Join-Path $runtime "web.pid"
$apiOutLog = Join-Path $logs "api.out.log"
$apiErrLog = Join-Path $logs "api.err.log"
$webOutLog = Join-Path $logs "web.out.log"
$webErrLog = Join-Path $logs "web.err.log"

. $helpers

if (-not (Test-Path $python)) {
    throw "Missing .venv\Scripts\python.exe. Please create the virtual environment and install Python dependencies first."
}

Normalize-ProcessPathEnvironment
$secrets = Ensure-WeatherWearSecrets -Root $root

function Write-StructuredRuntimeEvent {
    param(
        [string]$EventType,
        [string]$Message,
        [hashtable]$Payload = @{}
    )

    $eventPath = Join-Path $logs "app.events.jsonl"
    $eventJson = @{
        timestamp = [DateTimeOffset]::UtcNow.ToString("o")
        type = $EventType
        level = "info"
        message = $Message
        payload = $Payload
    } | ConvertTo-Json -Compress -Depth 6
    Add-Content -Path $eventPath -Value $eventJson -Encoding utf8
}

function Get-ManagedProcess {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($pidText -notmatch "^\d+$") {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    try {
        return Get-Process -Id ([int]$pidText) -ErrorAction Stop
    }
    catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
}

function Get-LogTail {
    param(
        [string]$Path,
        [int]$Lines = 16
    )

    if (-not (Test-Path $Path)) {
        return ""
    }
    return (Get-Content $Path -Tail $Lines -ErrorAction SilentlyContinue) -join [Environment]::NewLine
}

function Stop-ManagedProcessTree {
    param(
        [string]$PidFile,
        [string]$Name
    )

    $process = Get-ManagedProcess -PidFile $PidFile
    if ($process) {
        cmd.exe /c "taskkill /PID $($process.Id) /T /F 2>&1" | Out-Null
        Write-Host "Stopped $Name process tree ($($process.Id))." -ForegroundColor DarkYellow
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Start-ManagedProcess {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$PidFile,
        [string]$StdOutPath,
        [string]$StdErrPath,
        [hashtable]$EnvVars = @{}
    )

    Remove-Item $StdOutPath -Force -ErrorAction SilentlyContinue
    Remove-Item $StdErrPath -Force -ErrorAction SilentlyContinue

    $oldValues = @{}
    foreach ($key in $EnvVars.Keys) {
        $oldValues[$key] = [System.Environment]::GetEnvironmentVariable($key, "Process")
        [System.Environment]::SetEnvironmentVariable($key, [string]$EnvVars[$key], "Process")
    }

    try {
        $process = Start-Process $Executable `
            -WorkingDirectory $WorkingDirectory `
            -ArgumentList $Arguments `
            -WindowStyle Hidden `
            -RedirectStandardOutput $StdOutPath `
            -RedirectStandardError $StdErrPath `
            -PassThru
        Set-Content -Path $PidFile -Value $process.Id -Encoding ascii
        return $process
    }
    finally {
        foreach ($key in $EnvVars.Keys) {
            [System.Environment]::SetEnvironmentVariable($key, $oldValues[$key], "Process")
        }
    }
}

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$DisplayName,
        [string]$PidFile,
        [string]$StdOutPath,
        [string]$StdErrPath,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening -Port $Port) {
            return $true
        }

        $process = Get-ManagedProcess -PidFile $PidFile
        if (-not $process) {
            $stdoutTail = Get-LogTail -Path $StdOutPath
            $stderrTail = Get-LogTail -Path $StdErrPath
            throw "$DisplayName exited before it became ready on port $Port.`n--- stdout ---`n$stdoutTail`n--- stderr ---`n$stderrTail"
        }

        Start-Sleep -Milliseconds 400
    }

    $stdoutTail = Get-LogTail -Path $StdOutPath
    $stderrTail = Get-LogTail -Path $StdErrPath
    throw "$DisplayName did not become ready on port $Port within $TimeoutSeconds seconds.`n--- stdout ---`n$stdoutTail`n--- stderr ---`n$stderrTail"
}

function Ensure-FrontendDependencies {
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
        $env:npm_config_cache = Join-Path $frontend ".npm-cache"
        Write-Host "Frontend dependencies not found. Installing npm packages..." -ForegroundColor Yellow
        Push-Location $frontend
        try {
            & $npm install
            if ($LASTEXITCODE -ne 0) {
                throw "npm install failed."
            }
        }
        finally {
            Pop-Location
        }
    }
}

function Start-FrontendWithRecovery {
    param(
        [int]$Port,
        [int]$ApiPort
    )

    Stop-ManagedProcessTree -PidFile $webPidFile -Name "frontend"

    Start-ManagedProcess `
        -Executable $npm `
        -Arguments @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$Port", "--strictPort") `
        -WorkingDirectory $frontend `
        -PidFile $webPidFile `
        -StdOutPath $webOutLog `
        -StdErrPath $webErrLog `
        -EnvVars @{
            WEATHERWEAR_OPEN_BROWSER = "0"
            WEATHERWEAR_API_PORT = "$ApiPort"
            WEATHERWEAR_API_URL = "http://127.0.0.1:$ApiPort"
            npm_config_cache = (Join-Path $frontend ".npm-cache")
        } | Out-Null

    try {
        Wait-ForPort `
            -Port $Port `
            -DisplayName "WeatherWear React frontend" `
            -PidFile $webPidFile `
            -StdOutPath $webOutLog `
            -StdErrPath $webErrLog | Out-Null
    }
    catch {
        $details = "$($_.Exception.Message)`n$(Get-LogTail -Path $webErrLog)"
        Stop-ManagedProcessTree -PidFile $webPidFile -Name "frontend"
        if ($details -match "spawn EPERM") {
            Write-Host "Frontend hit spawn EPERM. Rebuilding esbuild and retrying once..." -ForegroundColor Yellow
            Push-Location $frontend
            try {
                $env:npm_config_cache = Join-Path $frontend ".npm-cache"
                & $npm rebuild esbuild
                if ($LASTEXITCODE -ne 0) {
                    throw "npm rebuild esbuild failed."
                }
            }
            finally {
                Pop-Location
            }

            Start-ManagedProcess `
                -Executable $npm `
                -Arguments @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$Port", "--strictPort") `
                -WorkingDirectory $frontend `
                -PidFile $webPidFile `
                -StdOutPath $webOutLog `
                -StdErrPath $webErrLog `
                -EnvVars @{
                    WEATHERWEAR_OPEN_BROWSER = "0"
                    WEATHERWEAR_API_PORT = "$ApiPort"
                    WEATHERWEAR_API_URL = "http://127.0.0.1:$ApiPort"
                    npm_config_cache = (Join-Path $frontend ".npm-cache")
                } | Out-Null

            Wait-ForPort `
                -Port $Port `
                -DisplayName "WeatherWear React frontend" `
                -PidFile $webPidFile `
                -StdOutPath $webOutLog `
                -StdErrPath $webErrLog | Out-Null
            return
        }
        throw
    }
}

Write-Host "Starting WeatherWear in single-window mode..." -ForegroundColor Cyan

if ($secrets.PinGenerated) {
    Write-Host "Generated a local developer PIN: $($secrets.DevPin)" -ForegroundColor Yellow
}

Ensure-FrontendDependencies

$apiReady = $false
$apiStartedThisRun = $false
$apiPort = $null
$restartManagedApi = $false
$portsPath = Get-PortManifestPath -Root $root
$managedApiProcess = Get-ManagedProcess -PidFile $apiPidFile
if ($managedApiProcess -and (Test-Path $portsPath)) {
    try {
        $manifest = Get-Content $portsPath -Raw | ConvertFrom-Json
        $candidatePort = [int]($manifest.api.port)
        if ($candidatePort -and (Test-PortListening -Port $candidatePort)) {
            $apiStatus = Get-WeatherWearApiCompatibilityStatus -BaseUrl "http://127.0.0.1:$candidatePort" -WorkspaceRoot $root
            if ($apiStatus.Kind -eq "compatible") {
                $apiPort = $candidatePort
                $apiReady = $true
                Write-Host "API already available on http://127.0.0.1:$apiPort" -ForegroundColor DarkGreen
            }
            else {
                $restartManagedApi = $true
            }
        }
        else {
            $restartManagedApi = $true
        }
    }
    catch {
        $restartManagedApi = $true
    }
}

if (-not $apiPort) {
    $apiPort = Get-FreeTcpPort -StartPort 8000 -EndPort 8050
    if ($apiPort -ne 8000) {
        Write-Host "Port 8000 is occupied. WeatherWear API will use http://127.0.0.1:$apiPort" -ForegroundColor Yellow
    }
}

if (-not $apiReady) {
    if ($managedApiProcess -and $restartManagedApi) {
        Stop-ManagedProcessTree -PidFile $apiPidFile -Name "API"
        $managedApiProcess = $null
    }

    $apiProcess = Get-ManagedProcess -PidFile $apiPidFile
    if (-not $apiProcess) {
        Write-Host "Launching API in background..." -ForegroundColor DarkCyan
        Start-ManagedProcess `
            -Executable $python `
            -Arguments @("-m", "weatherwear.api.server") `
            -WorkingDirectory $root `
            -PidFile $apiPidFile `
            -StdOutPath $apiOutLog `
            -StdErrPath $apiErrLog `
            -EnvVars @{
                WEATHERWEAR_API_PORT = "$apiPort"
            } | Out-Null
        $apiStartedThisRun = $true
    }
}

$webPort = Get-FreeTcpPort -StartPort 5173 -EndPort 5205
Write-Host "Launching React frontend in background on port $webPort..." -ForegroundColor DarkCyan

try {
    Wait-ForPort `
        -Port $apiPort `
        -DisplayName "WeatherWear API" `
        -PidFile $apiPidFile `
        -StdOutPath $apiOutLog `
        -StdErrPath $apiErrLog | Out-Null

    Start-FrontendWithRecovery -Port $webPort -ApiPort $apiPort
}
catch {
    $message = $_.Exception.Message
    if ($apiStartedThisRun -and $message -match "WeatherWear API") {
        Stop-ManagedProcessTree -PidFile $apiPidFile -Name "API"
    }
    Stop-ManagedProcessTree -PidFile $webPidFile -Name "frontend"
    throw
}

$apiListeningPid = Get-ListeningProcessId -Port $apiPort
if ($apiListeningPid) {
    Set-Content -Path $apiPidFile -Value $apiListeningPid -Encoding ascii
}

$webListeningPid = Get-ListeningProcessId -Port $webPort
if ($webListeningPid) {
    Set-Content -Path $webPidFile -Value $webListeningPid -Encoding ascii
}

Write-PortManifest -Root $root -ApiPort $apiPort -WebPort $webPort
Write-StructuredRuntimeEvent -EventType "launcher.started" -Message "WeatherWear launcher started." -Payload @{
    api_port = $apiPort
    web_port = $webPort
}

Write-Host "WeatherWear is ready." -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$webPort" -ForegroundColor Gray
Write-Host "API:      http://127.0.0.1:$apiPort" -ForegroundColor Gray
Write-Host "Runtime:  $runtime" -ForegroundColor Gray
Write-Host "Logs:     $logs" -ForegroundColor Gray
Write-Host "Developer PIN: $($secrets.DevPin)" -ForegroundColor Gray
Write-Host "Stop with .\stop_all.ps1 if you want to close background processes." -ForegroundColor Yellow

if ($env:WEATHERWEAR_SKIP_BROWSER -ne "1") {
    $opened = Open-UrlInBrowser -Url "http://127.0.0.1:$webPort"
    if (-not $opened) {
        Write-Host "Browser did not open automatically. Please open http://127.0.0.1:$webPort manually." -ForegroundColor Yellow
    }
}
