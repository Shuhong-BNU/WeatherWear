$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pwsh = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

Write-Host "Starting WeatherWear API and React frontend in developer mode..." -ForegroundColor Cyan
Start-Process $pwsh -WorkingDirectory $root -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $root "run_api.ps1")
)
Start-Sleep -Seconds 2
Start-Process $pwsh -WorkingDirectory $root -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $root "run_web.ps1")
)
