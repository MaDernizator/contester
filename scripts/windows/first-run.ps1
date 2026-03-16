param(
    [int]$TimeoutSec = 240
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Assert-DockerAvailable {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker command was not found. Install Docker Desktop first."
    }

    try {
        docker version | Out-Null
    }
    catch {
        throw "Docker Desktop is installed but not running. Start Docker Desktop and try again."
    }

    try {
        docker compose version | Out-Null
    }
    catch {
        throw "Docker Compose is not available. Update Docker Desktop and try again."
    }
}

function Get-EnvFileValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$DefaultValue
    )

    if (-not (Test-Path $Path)) {
        return $DefaultValue
    }

    $match = Select-String -Path $Path -Pattern "^${Key}=(.*)$" | Select-Object -First 1
    if ($null -eq $match) {
        return $DefaultValue
    }

    return $match.Matches[0].Groups[1].Value.Trim()
}

function Ensure-EnvFile {
    param(
        [string]$EnvExamplePath,
        [string]$EnvPath
    )

    if (-not (Test-Path $EnvExamplePath)) {
        throw ".env.example was not found in repository root."
    }

    if (Test-Path $EnvPath) {
        Write-Host ".env already exists. Reusing current configuration." -ForegroundColor Yellow
        return
    }

    Copy-Item -Path $EnvExamplePath -Destination $EnvPath

    $generatedSecret = (
        [guid]::NewGuid().ToString("N") +
        [guid]::NewGuid().ToString("N")
    )

    $content = Get-Content -Path $EnvPath -Raw
    $content = $content.Replace(
        "SECRET_KEY=change-me-local-network-secret",
        "SECRET_KEY=$generatedSecret"
    )
    Set-Content -Path $EnvPath -Value $content -Encoding UTF8

    Write-Host ".env created automatically." -ForegroundColor Green
}

function Wait-For-Health {
    param(
        [string]$Url,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec 5
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for health endpoint: $Url"
}

function Get-LocalIPv4Addresses {
    try {
        return Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -ne "0.0.0.0"
            } |
            Select-Object -ExpandProperty IPAddress -Unique
    }
    catch {
        return @()
    }
}

$repoRoot = Get-RepoRoot
Set-Location $repoRoot

$envExamplePath = Join-Path $repoRoot ".env.example"
$envPath = Join-Path $repoRoot ".env"

Write-Step "Checking Docker"
Assert-DockerAvailable

Write-Step "Preparing environment file"
Ensure-EnvFile -EnvExamplePath $envExamplePath -EnvPath $envPath

$frontendPort = Get-EnvFileValue -Path $envPath -Key "FRONTEND_PORT" -DefaultValue "8080"
$healthUrl = "http://127.0.0.1:$frontendPort/api/v1/health"

Write-Step "Starting Contester"
docker compose up --build -d

Write-Step "Waiting for backend health through frontend proxy"
Wait-For-Health -Url $healthUrl -TimeoutSec $TimeoutSec

$localIpAddresses = Get-LocalIPv4Addresses

Write-Step "Contester is ready"
Write-Host "Local URL:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:$frontendPort"

if ($localIpAddresses.Count -gt 0) {
    Write-Host ""
    Write-Host "LAN URLs:" -ForegroundColor Green
    foreach ($ip in $localIpAddresses) {
        Write-Host "  http://$ip`:$frontendPort"
    }
}

Write-Host ""
Write-Host "Next step:" -ForegroundColor Yellow
Write-Host "  .\scripts\windows\create-admin.ps1"