$ErrorActionPreference = "Stop"

function Ensure-WeatherWearDirectories {
    param([string]$Root)

    foreach ($path in @(
        (Join-Path $Root ".runtime"),
        (Join-Path $Root ".runtime\logs"),
        (Join-Path $Root ".runtime\state")
    )) {
        New-Item -ItemType Directory -Force $path | Out-Null
    }
}

function Get-EnvMap {
    param([string]$EnvFile)

    $values = @{}
    if (-not (Test-Path $EnvFile)) {
        return $values
    }

    foreach ($line in Get-Content $EnvFile -ErrorAction SilentlyContinue) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        if ($line.TrimStart().StartsWith("#")) {
            continue
        }
        $parts = $line -split "=", 2
        if ($parts.Length -ne 2) {
            continue
        }
        $values[$parts[0].Trim()] = $parts[1]
    }
    return $values
}

function Set-EnvValue {
    param(
        [string]$EnvFile,
        [string]$Key,
        [string]$Value
    )

    if (-not (Test-Path $EnvFile)) {
        Set-Content -Path $EnvFile -Value "" -Encoding utf8
    }

    $lines = @(Get-Content $EnvFile -ErrorAction SilentlyContinue)
    $updated = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match "^$([regex]::Escape($Key))=") {
            $lines[$i] = "$Key=$Value"
            $updated = $true
        }
    }
    if (-not $updated) {
        $lines += "$Key=$Value"
    }
    Set-Content -Path $EnvFile -Value $lines -Encoding utf8
}

function New-RandomDigits {
    param([int]$Length = 6)

    -join (1..$Length | ForEach-Object { Get-Random -Minimum 0 -Maximum 10 })
}

function New-RandomSecret {
    param([int]$Bytes = 32)

    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer)
}

function Ensure-WeatherWearSecrets {
    param([string]$Root)

    Ensure-WeatherWearDirectories -Root $Root
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) {
        Set-Content -Path $envFile -Value "" -Encoding utf8
    }

    $values = Get-EnvMap -EnvFile $envFile
    $generatedPin = $null
    $generatedSecret = $null

    if (-not $values.ContainsKey("WEATHERWEAR_DEV_PIN") -or [string]::IsNullOrWhiteSpace($values["WEATHERWEAR_DEV_PIN"])) {
        $generatedPin = New-RandomDigits
        Set-EnvValue -EnvFile $envFile -Key "WEATHERWEAR_DEV_PIN" -Value $generatedPin
        $values["WEATHERWEAR_DEV_PIN"] = $generatedPin
    }

    if (-not $values.ContainsKey("WEATHERWEAR_SESSION_SECRET") -or [string]::IsNullOrWhiteSpace($values["WEATHERWEAR_SESSION_SECRET"])) {
        $generatedSecret = New-RandomSecret
        Set-EnvValue -EnvFile $envFile -Key "WEATHERWEAR_SESSION_SECRET" -Value $generatedSecret
        $values["WEATHERWEAR_SESSION_SECRET"] = $generatedSecret
    }

    [PSCustomObject]@{
        EnvFile = $envFile
        DevPin = $values["WEATHERWEAR_DEV_PIN"]
        SessionSecret = $values["WEATHERWEAR_SESSION_SECRET"]
        PinGenerated = [bool]$generatedPin
        SecretGenerated = [bool]$generatedSecret
    }
}

function Normalize-ProcessPathEnvironment {
    $pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $pathValue) {
        $pathValue = [System.Environment]::GetEnvironmentVariable("PATH", "Process")
    }

    if ($pathValue) {
        [System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
        [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    }
}

function Test-PortListening {
    param([int]$Port)

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(300)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($async)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Get-ListeningProcessId {
    param([int]$Port)

    $lines = cmd /c "netstat -ano -p tcp"
    foreach ($line in $lines) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    return $null
}

function Stop-ProcessTreeByPid {
    param(
        [int]$ProcessId,
        [string]$Name = "process"
    )

    if (-not $ProcessId) {
        return
    }
    cmd.exe /c "taskkill /PID $ProcessId /T /F 2>&1" | Out-Null
    Write-Host "Stopped $Name process tree ($ProcessId)." -ForegroundColor DarkYellow
}

function Get-WeatherWearApiCompatibilityStatus {
    param(
        [string]$BaseUrl = "http://127.0.0.1:8000",
        [string]$WorkspaceRoot = ""
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing "$BaseUrl/openapi.json" -TimeoutSec 5
        $document = $response.Content | ConvertFrom-Json
        $title = [string]($document.info.title)
        if ($title -ne "WeatherWear API") {
            return @{
                Kind = "other"
                Message = "Port responds, but it is not a WeatherWear API instance."
            }
        }

        $pathNames = @()
        if ($document.paths) {
            $pathNames = @($document.paths.PSObject.Properties.Name)
        }
        $queryProps = $document.components.schemas.QueryRequest.properties
        $queryPropNames = @()
        if ($queryProps) {
            $queryPropNames = @($queryProps.PSObject.Properties.Name)
        }

        $requiredFields = @("gender", "occasion_text", "target_date")
        $missingFields = @($requiredFields | Where-Object { $queryPropNames -notcontains $_ })
        $hasClientEventRoute = $pathNames -contains "/api/logs/client-event"

        if ($missingFields.Count -eq 0 -and $hasClientEventRoute) {
            if ($WorkspaceRoot) {
                try {
                    $healthResponse = Invoke-WebRequest -UseBasicParsing "$BaseUrl/api/health/runtime" -TimeoutSec 5
                    $health = $healthResponse.Content | ConvertFrom-Json
                    $remoteRoot = [string]($health.workspace_root)
                    if ($remoteRoot) {
                        $normalizedLocalRoot = [System.IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd('\').ToLowerInvariant()
                        $normalizedRemoteRoot = [System.IO.Path]::GetFullPath($remoteRoot).TrimEnd('\').ToLowerInvariant()
                        if ($normalizedLocalRoot -ne $normalizedRemoteRoot) {
                            return @{
                                Kind = "foreign"
                                Message = "Port responds with another WeatherWear workspace: $remoteRoot"
                            }
                        }
                    }
                }
                catch {
                    return @{
                        Kind = "stale"
                        Message = "WeatherWear API schema is compatible, but workspace identity could not be verified."
                    }
                }
            }
            return @{
                Kind = "compatible"
                Message = "WeatherWear API is compatible with the current frontend."
            }
        }

        $parts = @()
        if ($missingFields.Count -gt 0) {
            $parts += "missing query fields: $($missingFields -join ', ')"
        }
        if (-not $hasClientEventRoute) {
            $parts += "missing /api/logs/client-event"
        }
        return @{
            Kind = "stale"
            Message = "Detected an older WeatherWear API schema: $($parts -join '; ')"
        }
    }
    catch {
        return @{
            Kind = "unreachable"
            Message = $_.Exception.Message
        }
    }
}

function Resolve-WeatherWearApiPort {
    param(
        [int]$PreferredPort = 8000,
        [int]$EndPort = 8050,
        [string]$WorkspaceRoot = ""
    )

    $freePort = $null
    for ($port = $PreferredPort; $port -le $EndPort; $port++) {
        if (Test-PortListening -Port $port) {
            $status = Get-WeatherWearApiCompatibilityStatus -BaseUrl "http://127.0.0.1:$port" -WorkspaceRoot $WorkspaceRoot
            if ($status.Kind -eq "compatible") {
                return $port
            }
            continue
        }

        if (-not $freePort) {
            $freePort = $port
        }
    }

    if ($freePort) {
        return $freePort
    }

    throw "No compatible or free WeatherWear API port found between $PreferredPort and $EndPort."
}

function Get-FreeTcpPort {
    param(
        [int]$StartPort = 5173,
        [int]$EndPort = 5205
    )

    for ($port = $StartPort; $port -le $EndPort; $port++) {
        if (-not (Test-PortListening -Port $port)) {
            return $port
        }
    }
    throw "No free TCP port found between $StartPort and $EndPort."
}

function Get-PortManifestPath {
    param([string]$Root)
    return (Join-Path $Root ".runtime\ports.json")
}

function Write-PortManifest {
    param(
        [string]$Root,
        [int]$ApiPort,
        [int]$WebPort
    )

    $manifestPath = Get-PortManifestPath -Root $Root
    $payload = @{
        api = @{
            port = $ApiPort
            url = "http://127.0.0.1:$ApiPort"
        }
        web = @{
            port = $WebPort
            url = "http://127.0.0.1:$WebPort"
        }
    } | ConvertTo-Json -Depth 4
    Set-Content -Path $manifestPath -Value $payload -Encoding utf8
}

function Open-UrlInBrowser {
    param([string]$Url)

    try {
        & cmd.exe /c start "" $Url | Out-Null
        return $true
    }
    catch {
        try {
            Start-Process "explorer.exe" -ArgumentList $Url | Out-Null
            return $true
        }
        catch {
            return $false
        }
    }
}
