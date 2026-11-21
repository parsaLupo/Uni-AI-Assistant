# Repository secret scan (mirrors the CI `secret-scan` job) plus release-file
# hygiene checks. Prints file names/commit ids only, never the matched value.
#
#   scripts/secret-scan.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

Push-Location $script:RepoRoot
try {
    # High-confidence live-credential shapes.
    $credentialPatterns = @(
        'gsk_[A-Za-z0-9]{20,}',
        'sk-[A-Za-z0-9]{20,}',
        'AKIA[0-9A-Z]{16}',
        '-----BEGIN [A-Z ]*PRIVATE KEY-----'
    )
    # Broader assignment shapes: generic API/secret keys and the removed public
    # demo password. These are scanned in the working tree; the demo literal is
    # intentionally not part of the history check because it is a known public
    # value retained in checkpoint refs and already rotated (see M1).
    $broadPatterns = @(
        'demo[-_ ]passw0rd',
        '(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)[[:space:]]*[:=][[:space:]]*["''][^"'']{8,}["'']'
    )
    $knownNonSecrets = @(
        'dev-only-insecure-key-do-not-use-in-production'
    )
    $trackedPattern = ($credentialPatterns + $broadPatterns) -join '|'
    # History scanning uses only high-confidence live-credential shapes. The
    # generic assignment patterns stay on the current tree; immutable history
    # can otherwise raise false positives that cannot be fixed without a rewrite.
    $historyPattern = $credentialPatterns -join '|'
    $failures = 0

    Write-Host "Scanning tracked files for credential patterns..."
    $trackedMatches = & git grep -nIE -i $trackedPattern -- . 2>$null
    if ($trackedMatches) {
        $trackedMatches = $trackedMatches | Where-Object {
            $line = $_
            -not ($knownNonSecrets | Where-Object { $line -like "*$_*" })
        }
    }
    $trackedFiles = @()
    if ($trackedMatches) {
        $trackedFiles = $trackedMatches |
            ForEach-Object { ($_ -split ':', 2)[0] } |
            Sort-Object -Unique
    }
    if ($trackedFiles.Count -gt 0) {
        $failures++
        Write-Host "FAIL  credential-looking strings in tracked files:"
        foreach ($file in $trackedFiles) { Write-Host "  - $file" }
        Write-Host "      Rotate the key, remove it from the working tree, and report the history risk."
    } else {
        Write-Host "PASS  no credential patterns in tracked files"
    }

    Write-Host "Scanning Git history (all commits)..."
    $historyCommits = & git log --all -i -G $historyPattern --pretty=oneline -- . 2>$null
    if ($historyCommits) {
        $failures++
        Write-Host "FAIL  credential pattern appears in history:"
        foreach ($commit in $historyCommits) { Write-Host "  - $commit" }
        Write-Host "      Do NOT rewrite history automatically; report and plan a coordinated rotation."
    } else {
        Write-Host "PASS  no credential patterns in Git history"
    }

    Write-Host "Checking tracked environment/key/backup files..."
    $tracked = & git ls-files
    $sensitive = $tracked | Where-Object {
        ($_ -match '(^|/)\.env($|\.)' -and $_ -notmatch '\.example$') -or
        ($_ -match '\.(pem|key|p12|pfx|dump|bak)$') -or
        ($_ -match '(^|/)backups/')
    }
    if ($sensitive) {
        $failures++
        Write-Host "FAIL  sensitive/local files are tracked:"
        foreach ($file in $sensitive) { Write-Host "  - $file" }
    } else {
        Write-Host "PASS  no tracked .env, private key, dump, or backup file"
    }

    Write-Host "Checking ignore rules for local state..."
    $ignoredChecks = @(".env", "backend/.env", "backups/", "local/", "pdfs/", "frontend/test-results/", "frontend/tests/")
    $notIgnored = @()
    foreach ($path in $ignoredChecks) {
        & git check-ignore -q $path
        if ($LASTEXITCODE -ne 0) { $notIgnored += $path }
    }
    if ($notIgnored.Count -gt 0) {
        $failures++
        Write-Host "FAIL  these local paths are not ignored: $($notIgnored -join ', ')"
    } else {
        Write-Host "PASS  secrets, backups, local credentials, PDFs and test output are ignored"
    }

    if ($failures -gt 0) {
        Write-Host ""
        Write-Host "Secret scan found $failures issue(s). Not GitHub-ready."
        exit 1
    }
    Write-Host ""
    Write-Host "Secret scan clean."
} finally {
    Pop-Location
}
