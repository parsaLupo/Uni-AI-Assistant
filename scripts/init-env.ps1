# Generate a local `.env` for the release stack with unique random secrets.
#
#   scripts/init-env.ps1
#   scripts/init-env.ps1 -AiProvider groq -AiKey '<key>'
#
# Never overwrites an existing file unless -Force is passed. Secrets are written
# only to the gitignored .env and are never printed.
[CmdletBinding()]
param(
    [string]$OutFile = ".env",
    [int]$AppPort = 8080,
    [ValidateSet("mock", "groq")][string]$AiProvider = "mock",
    [string]$AiKey = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

function New-UrlSafeSecret {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($buffer).Replace("+", "-").Replace("/", "_").TrimEnd("=")
}

function New-AlphanumericPassword {
    param([int]$Length = 24)
    $alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $chars = for ($i = 0; $i -lt $Length; $i++) {
        $alphabet[$bytes[$i] % $alphabet.Length]
    }
    return -join $chars
}

$root = Split-Path -Parent $PSScriptRoot
$template = Join-Path $root ".env.example"
$target = Resolve-EnvPath $OutFile

if (-not (Test-Path $template)) { throw "Template not found: $template" }
if ((Test-Path $target) -and -not $Force) {
    throw "$target already exists. Use -Force to replace it deliberately."
}
if ($AiProvider -eq "groq" -and [string]::IsNullOrWhiteSpace($AiKey)) {
    throw "-AiKey is required when -AiProvider groq."
}

$content = Get-Content -LiteralPath $template -Raw
$secret = New-UrlSafeSecret 48
$dbPassword = New-AlphanumericPassword 24
$demoPassword = "Demo-" + (New-AlphanumericPassword 18)

$content = $content -replace '(?m)^DJANGO_SECRET_KEY=.*$', "DJANGO_SECRET_KEY=$secret"
$content = $content -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$dbPassword"
$content = $content -replace '(?m)^DEMO_PASSWORD=.*$', "DEMO_PASSWORD=$demoPassword"
$content = $content -replace '(?m)^APP_PORT=.*$', "APP_PORT=$AppPort"
$content = $content -replace '(?m)^AI_PROVIDER=.*$', "AI_PROVIDER=$AiProvider"
if ($AiProvider -eq "groq") {
    $content = $content -replace '(?m)^AI_PROVIDER_API_KEY=.*$', "AI_PROVIDER_API_KEY=$AiKey"
    # The default Groq model may change; leave AI_MODEL empty to use the
    # adapter's pinned default unless the operator sets it.
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($target, $content, $utf8NoBom)

Write-Host "Wrote $target (gitignored)."
Write-Host "Local URL: http://localhost:$AppPort"
Write-Host "AI provider: $AiProvider"
Write-Host "Demo credentials: run scripts/show-demo-credentials.ps1 (local only)."
Write-Host "Next: scripts/deploy-local.ps1"
