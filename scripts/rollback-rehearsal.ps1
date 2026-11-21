# Safe rollback rehearsal: prove that a bad image tag fails visibly and that
# the previous tagged image brings the backend back healthy. No data is touched.
#
#   scripts/rollback-rehearsal.ps1
#   scripts/rollback-rehearsal.ps1 -ProjectName usa-phase16-fresh -BaseUrl http://localhost:18080
[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [string]$BaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$base = $BaseUrl.TrimEnd("/")
$envMap = Get-DotEnv (Resolve-EnvPath $EnvFile)
$originalTag = if ($envMap["IMAGE_TAG"]) { $envMap["IMAGE_TAG"] } else { "local" }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$rehearsalTag = "rehearsal-$stamp"

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName

    Write-Host "Tagging current images as $rehearsalTag..."
    & docker tag "university-assistant-backend:$originalTag" "university-assistant-backend:$rehearsalTag"
    Assert-ExitCode "docker tag backend"
    & docker tag "university-assistant-web:$originalTag" "university-assistant-web:$rehearsalTag"
    Assert-ExitCode "docker tag web"

    Write-Host "Simulating a deployment with a missing image tag (must fail)..."
    $env:IMAGE_TAG = "__missing_image__"
    & docker @compose up -d --no-build backend *> $null
    $badExit = $LASTEXITCODE
    if ($badExit -eq 0) {
        throw "Expected the missing-image deployment to fail, but Compose returned success."
    }
    Write-Host "PASS  missing image failed with exit code $badExit"

    Write-Host "Rolling back to the recorded image tag $rehearsalTag..."
    $env:IMAGE_TAG = $rehearsalTag
    & docker @compose up -d --no-build backend
    Assert-ExitCode "rollback up backend"
    if (-not (Wait-HttpOk -Url "$base/health/ready" -TimeoutSeconds 90)) {
        throw "Backend did not become ready after rollback."
    }
    Write-Host "PASS  rollback restored a ready backend"

    $env:IMAGE_TAG = $originalTag
    & docker @compose up -d --no-build backend *> $null
    Assert-ExitCode "restore original image tag"
    if (-not (Wait-HttpOk -Url "$base/health/ready" -TimeoutSeconds 90)) {
        throw "Backend did not become ready after restoring the original tag."
    }
    Write-Host "PASS  original image tag restored and ready"
    Write-Host ""
    Write-Host "Rollback rehearsal passed (backend + web images, no database changes)."
} finally {
    $env:IMAGE_TAG = $originalTag
    Pop-Location
}
