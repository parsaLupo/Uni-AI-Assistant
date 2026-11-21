# Shared helpers for the Phase 16 local-release scripts (dot-sourced).
# PowerShell 7 on Windows is the primary target; the documented raw commands in
# DEPLOYMENT.md are the portable equivalent.

$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:DefaultProject = "university-assistant"

function Get-DotEnv {
    param([Parameter(Mandatory)][string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $text = $line.Trim()
        if (-not $text -or $text.StartsWith('#') -or -not $text.Contains('=')) { continue }
        $index = $text.IndexOf('=')
        $key = $text.Substring(0, $index).Trim()
        $value = $text.Substring($index + 1).Trim().Trim('"').Trim("'")
        if ($key) { $map[$key] = $value }
    }
    return $map
}

function Get-RequiredEnv {
    param(
        [Parameter(Mandatory)][hashtable]$Map,
        [Parameter(Mandatory)][string]$Key
    )
    $value = [string]$Map[$Key]
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Environment value '$Key' is missing from the env file. Run scripts/init-env.ps1 first."
    }
    return $value
}

function Resolve-EnvPath {
    param([string]$EnvFile = ".env")
    if ([IO.Path]::IsPathRooted($EnvFile)) { return $EnvFile }
    return (Join-Path $script:RepoRoot $EnvFile)
}

function Get-ComposeArgs {
    param(
        [string]$EnvFile = ".env",
        [string]$ProjectName = $script:DefaultProject
    )
    $resolved = Resolve-EnvPath $EnvFile
    if (-not (Test-Path $resolved)) {
        throw "Env file not found: $resolved. Copy .env.example to .env or run scripts/init-env.ps1."
    }
    # Compose interpolates ${ENV_FILE} for each service's env_file entry; make
    # it point at the same file chosen on the command line (fresh-deploy tests
    # use a separate .env.fresh without touching the primary .env).
    $env:ENV_FILE = (Split-Path -Leaf $resolved)
    return @("compose", "--env-file", $resolved, "-p", $ProjectName)
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 4
            if ($response.StatusCode -eq 200) { return $true }
        } catch {
            # Service still starting; retry until the deadline.
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Assert-ExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE. See the command output above."
    }
}
