param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$helpers = Join-Path $root "scripts\RuntimeHelpers.ps1"

. $helpers

if (-not (Test-Path (Join-Path $frontend "package.json"))) {
    throw "Missing frontend\package.json. Please verify that the React frontend exists."
}

Normalize-ProcessPathEnvironment
$secrets = Ensure-WeatherWearSecrets -Root $root
$webPort = Get-FreeTcpPort -StartPort 5173 -EndPort 5205
$apiPort = 8000
$portsPath = Get-PortManifestPath -Root $root
if (Test-Path $portsPath) {
    try {
        $ports = Get-Content $portsPath -Raw | ConvertFrom-Json
        if ($ports.api.port) {
            $apiPort = [int]$ports.api.port
        }
    }
    catch {
        $apiPort = Resolve-WeatherWearApiPort -PreferredPort 8000 -EndPort 8050 -WorkspaceRoot $root
    }
}
else {
    $apiPort = Resolve-WeatherWearApiPort -PreferredPort 8000 -EndPort 8050 -WorkspaceRoot $root
}

if ($secrets.PinGenerated) {
    Write-Host "Generated a local developer PIN: $($secrets.DevPin)" -ForegroundColor Yellow
}

Push-Location $frontend
try {
    $env:npm_config_cache = Join-Path $frontend ".npm-cache"
    if ($NoBrowser) {
        $env:WEATHERWEAR_OPEN_BROWSER = "0"
    }
    elseif (-not $env:WEATHERWEAR_OPEN_BROWSER) {
        $env:WEATHERWEAR_OPEN_BROWSER = "1"
    }
    $env:WEATHERWEAR_API_PORT = "$apiPort"
    $env:WEATHERWEAR_API_URL = "http://127.0.0.1:$apiPort"

    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
        Write-Host "node_modules not found. Installing frontend dependencies..." -ForegroundColor Yellow
        & $npm install
    }

    $viteArgs = @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$webPort", "--strictPort")
    Write-Host "Starting WeatherWear React frontend at http://127.0.0.1:$webPort" -ForegroundColor Cyan
    & $npm @viteArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend exited unexpectedly. Rebuilding esbuild and retrying once..." -ForegroundColor Yellow
        & $npm rebuild esbuild
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to rebuild esbuild."
        }
        & $npm @viteArgs
    }
}
finally {
    Pop-Location
}
