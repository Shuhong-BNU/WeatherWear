$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$helpers = Join-Path $root "scripts\RuntimeHelpers.ps1"

. $helpers

if (-not (Test-Path $python)) {
    throw "Missing .venv\Scripts\python.exe. Please create the virtual environment and install Python dependencies first."
}

Normalize-ProcessPathEnvironment
$secrets = Ensure-WeatherWearSecrets -Root $root
$apiPort = $null
$portsPath = Get-PortManifestPath -Root $root
$apiPidFile = Join-Path $root ".runtime\api.pid"
$managedApiProcess = $null
$restartManagedApi = $false
if (Test-Path $apiPidFile) {
    try {
        $managedApiProcess = Get-Process -Id ([int](Get-Content $apiPidFile | Select-Object -First 1)) -ErrorAction Stop
    }
    catch {
        Remove-Item $apiPidFile -Force -ErrorAction SilentlyContinue
    }
}

if ($secrets.PinGenerated) {
    Write-Host "Generated a local developer PIN: $($secrets.DevPin)" -ForegroundColor Yellow
}

if ($managedApiProcess -and (Test-Path $portsPath)) {
    try {
        $manifest = Get-Content $portsPath -Raw | ConvertFrom-Json
        $candidatePort = [int]($manifest.api.port)
        if ($candidatePort -and (Test-PortListening -Port $candidatePort)) {
            $apiStatus = Get-WeatherWearApiCompatibilityStatus -BaseUrl "http://127.0.0.1:$candidatePort" -WorkspaceRoot $root
            if ($apiStatus.Kind -eq "compatible") {
                Write-Host "WeatherWear API is already running on http://127.0.0.1:$candidatePort" -ForegroundColor DarkGreen
                return
            }
            $restartManagedApi = $true
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

if ($managedApiProcess -and $restartManagedApi) {
    Stop-ProcessTreeByPid -ProcessId $managedApiProcess.Id -Name "API"
    Remove-Item $apiPidFile -Force -ErrorAction SilentlyContinue
    $managedApiProcess = $null
}

Write-Host "Starting WeatherWear API at http://127.0.0.1:$apiPort" -ForegroundColor Cyan
$webPort = 0
if (Test-Path $portsPath) {
    try {
        $manifest = Get-Content $portsPath -Raw | ConvertFrom-Json
        if ($manifest.web.port) {
            $webPort = [int]($manifest.web.port)
        }
    }
    catch {
        $webPort = 0
    }
}
Write-PortManifest -Root $root -ApiPort $apiPort -WebPort $webPort
$env:WEATHERWEAR_API_PORT = "$apiPort"
& $python -m weatherwear.api.server
