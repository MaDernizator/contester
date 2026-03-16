$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker command was not found. Install Docker Desktop first."
}

try {
    docker compose exec backend flask --app wsgi create-admin
}
catch {
    throw "Failed to create admin. Make sure the containers are running: docker compose ps"
}