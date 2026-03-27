$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtime = Join-Path $root ".runtime"
$helpers = Join-Path $root "scripts\RuntimeHelpers.ps1"

. $helpers

foreach ($name in @("api", "web")) {
    $pidFile = Join-Path $runtime "$name.pid"
    if (-not (Test-Path $pidFile)) {
        continue
    }

    $pidText = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($pidText -match "^\d+$") {
        $result = cmd.exe /c "taskkill /PID $pidText /T /F 2>&1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Stopped $name process tree ($pidText)." -ForegroundColor Green
        }
        elseif ($result) {
            Write-Host ($result -join [Environment]::NewLine) -ForegroundColor DarkYellow
        }
        else {
            Write-Host "$name process ($pidText) is already stopped." -ForegroundColor DarkYellow
        }
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$portsPath = Get-PortManifestPath -Root $root
Remove-Item $portsPath -Force -ErrorAction SilentlyContinue

$eventPath = Join-Path $runtime "logs\app.events.jsonl"
if (Test-Path (Split-Path $eventPath -Parent)) {
    $payload = @{
        timestamp = [DateTimeOffset]::UtcNow.ToString("o")
        type = "launcher.stopped"
        level = "info"
        message = "WeatherWear launcher stopped."
        payload = @{}
    } | ConvertTo-Json -Compress -Depth 4
    Add-Content -Path $eventPath -Value $payload -Encoding utf8
}
