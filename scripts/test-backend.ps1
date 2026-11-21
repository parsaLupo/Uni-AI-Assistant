# Run the backend suite against a disposable PostgreSQL + pgvector container.
#
#   scripts/test-backend.ps1
#   scripts/test-backend.ps1 apps/common/tests -q
#
# SQLite is not supported (ADR-002), so the suite always talks to a real
# PostgreSQL server. This script starts a throwaway container on a free host
# port, points TEST_DATABASE_URL at it, runs pytest, and removes the container.
# It never touches the release stack's named volume or its database.
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

function Get-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
        return $listener.LocalEndpoint.Port
    } finally {
        $listener.Stop()
    }
}

$backendDir = Join-Path $script:RepoRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$image = "pgvector/pgvector:0.8.6-pg16"
$container = "usa-test-db-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$port = Get-FreePort
$password = "test-$([guid]::NewGuid().ToString('N'))"
$database = "usa_test"

Write-Host "Starting disposable PostgreSQL ($image) on port $port..."
& docker run --rm -d --name $container -p "${port}:5432" `
    -e "POSTGRES_DB=$database" -e "POSTGRES_USER=usa_test" -e "POSTGRES_PASSWORD=$password" `
    $image *> $null
Assert-ExitCode "docker run test database"

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker exec $container pg_isready -U usa_test -d $database *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        & docker logs --tail 40 $container
        throw "Disposable PostgreSQL did not become ready."
    }

    $env:TEST_DATABASE_URL = "postgresql://usa_test:$password@localhost:$port/$database"
    Push-Location $backendDir
    try {
        Write-Host "Running backend tests against $env:TEST_DATABASE_URL"
        & $python -m pytest @PytestArgs
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
        Remove-Item Env:\TEST_DATABASE_URL -ErrorAction SilentlyContinue
    }
    exit $exitCode
} finally {
    & docker rm -f $container *> $null
}
