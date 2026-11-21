# One-command local release deployment (Phase 16).
#
#   scripts/init-env.ps1
#   scripts/deploy-local.ps1
#
# The script builds the images, starts PostgreSQL + Redis, runs migrations as a
# separate controlled step, seeds reproducible demo data, starts the full stack,
# waits for readiness, and tags the images for rollback. Persistent volumes are
# never removed.
[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [switch]$SkipBuild,
    [switch]$SkipSeed
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$envPath = Resolve-EnvPath $EnvFile
$envMap = Get-DotEnv $envPath
if ($envMap.Count -eq 0) {
    throw "Env file missing or empty: $envPath. Run scripts/init-env.ps1 first."
}
$appPort = if ($envMap["APP_PORT"]) { [int]$envMap["APP_PORT"] } else { 8080 }
$imageTag = if ($envMap["IMAGE_TAG"]) { $envMap["IMAGE_TAG"] } else { "local" }

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName

    if (-not $SkipBuild) {
        Write-Host "[1/7] Building backend and web images..."
        & docker @compose build
        Assert-ExitCode "docker compose build"
    }

    Write-Host "[2/7] Starting PostgreSQL and Redis..."
    & docker @compose up -d db redis
    Assert-ExitCode "docker compose up db redis"

    Write-Host "[3/7] Waiting for PostgreSQL..."
    $dbReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker @compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' *> $null
        if ($LASTEXITCODE -eq 0) { $dbReady = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $dbReady) { throw "PostgreSQL did not become ready in time. See: docker compose logs db" }

    Write-Host "[4/7] Applying migrations (controlled, separate step)..."
    & docker @compose run --rm backend python manage.py migrate --noinput
    Assert-ExitCode "migrate"

    if (-not $SkipSeed) {
        Write-Host "[5/7] Seeding real dataset + demo accounts (idempotent)..."
        & docker @compose run --rm backend python manage.py seed_demo
        Assert-ExitCode "seed_demo"
    } else {
        Write-Host "[5/7] Skipping demo seed (-SkipSeed)."
    }

    Write-Host "[6/7] Starting the full stack..."
    & docker @compose up -d
    Assert-ExitCode "docker compose up"

    $readyUrl = "http://localhost:$appPort/health/ready/"
    Write-Host "[7/7] Waiting for $readyUrl ..."
    if (-not (Wait-HttpOk -Url $readyUrl -TimeoutSeconds 120)) {
        & docker @compose ps
        & docker @compose logs --tail 80 backend
        throw "Stack did not become ready at $readyUrl."
    }

    # Keep a rollback tag beside the working image set. The images are local
    # only (never pushed); `IMAGE_TAG=<tag> docker compose up -d --no-build`.
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $rollbackTag = "rollback-$stamp"
    foreach ($image in @(
            "university-assistant-backend:$imageTag",
            "university-assistant-web:$imageTag"
        )) {
        $target = ($image -replace ":$imageTag$", ":$rollbackTag")
        & docker tag $image $target
        Assert-ExitCode "docker tag $image"
    }
    $localDir = Join-Path $script:RepoRoot "local"
    New-Item -ItemType Directory -Force -Path $localDir | Out-Null
    $tagFile = Join-Path $localDir "last-rollback-tag.txt"
    [System.IO.File]::WriteAllText($tagFile, $rollbackTag, (New-Object System.Text.UTF8Encoding($false)))

    Write-Host ""
    Write-Host "Local release is ready."
    Write-Host "  App:          http://localhost:$appPort"
    Write-Host "  API health:   http://localhost:$appPort/api/v1/health/"
    Write-Host "  Liveness:     http://localhost:$appPort/health/live/"
    Write-Host "  Readiness:    http://localhost:$appPort/health/ready/"
    Write-Host "  Deep health:  http://localhost:$appPort/health/deep/"
    Write-Host "  Swagger UI:   http://localhost:$appPort/api/v1/schema/swagger-ui/"
    Write-Host "  Rollback tag: $rollbackTag (recorded in local/last-rollback-tag.txt)"
    Write-Host ""
    Write-Host "Demo password: scripts/show-demo-credentials.ps1 (local only)"
    Write-Host "Smoke test:    scripts/smoke-test.ps1 -BaseUrl http://localhost:$appPort"
} finally {
    Pop-Location
}

# Success is explicit: the readiness loop and helper commands leave a stale
# $LASTEXITCODE behind, which would otherwise make a successful deploy look
# like a failure to callers and CI.
exit 0
