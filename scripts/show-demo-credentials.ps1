# Print the local demo credentials from the gitignored .env file.
# LOCAL ONLY: never paste this output into an issue, chat, or commit.
[CmdletBinding()]
param([string]$EnvFile = ".env")

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

$envPath = Resolve-EnvPath $EnvFile
$map = Get-DotEnv $envPath
if ($map.Count -eq 0) { throw "Env file not found or empty: $envPath" }
$password = Get-RequiredEnv $map "DEMO_PASSWORD"

Write-Host "Local demo accounts (from $envPath):"
Write-Host "  SUPERADMIN  root@semnan.local        / $password"
Write-Host "  ADMIN       admin@semnan.local       / $password"
Write-Host "  STUDENT     student@semnan.local     / $password"
Write-Host "  PROFESSOR   professor@semnan.local   / $password"
Write-Host ""
Write-Host "These identities exist only after: docker compose run --rm backend python manage.py seed_demo"
Write-Host "Do not commit, screenshot, or share this output."
