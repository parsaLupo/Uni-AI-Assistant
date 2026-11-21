# Restore drill: back up, restore into a temporary database, verify core tables
# and run real Django ORM queries against the restored copy, then drop it.
#
#   scripts/restore-drill.ps1
#
# The primary database is never modified. Evidence is written to
# local/restore-drill-<timestamp>.txt (gitignored).
[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [string]$BackupFile = ""
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$envPath = Resolve-EnvPath $EnvFile
$envMap = Get-DotEnv $envPath
$tempDb = "usa_db_restore_drill"

function Get-TableCount {
    param([string]$Database, [string]$Table, [string]$User)
    $value = (& docker @compose exec -T db psql -U $User -d $Database -tAc "SELECT count(*) FROM $Table" 2>$null)
    return ("$value").Trim()
}

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName
    $dbUser = Get-RequiredEnv $envMap "POSTGRES_USER"
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $evidenceDir = Join-Path $script:RepoRoot "local"
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    $evidence = Join-Path $evidenceDir "restore-drill-$stamp.txt"
    $lines = [System.Collections.Generic.List[string]]::new()
    function Record([string]$text) {
        Write-Host $text
        $lines.Add($text)
    }

    if ([string]::IsNullOrWhiteSpace($BackupFile)) {
        $BackupFile = & "$PSScriptRoot\backup.ps1" -EnvFile $EnvFile -ProjectName $ProjectName
    }
    if (-not (Test-Path -LiteralPath $BackupFile)) { throw "Backup file not found: $BackupFile" }

    $sourceDb = "$(& docker @compose exec -T db sh -c 'printf %s "$POSTGRES_DB"')".Trim()
    if (-not $sourceDb) { throw "Could not read POSTGRES_DB." }
    Record "restore drill $stamp"
    Record "source database: $sourceDb"
    Record "backup: $BackupFile"

    # Start from a clean temporary database so stale drill data cannot pass.
    & docker @compose exec -T db dropdb -U $dbUser --if-exists $tempDb *> $null
    & docker @compose exec -T db createdb -U $dbUser -O $dbUser $tempDb
    Assert-ExitCode "create drill database"

    & "$PSScriptRoot\restore.ps1" -BackupFile $BackupFile -EnvFile $EnvFile -ProjectName $ProjectName -TargetDatabase $tempDb -Force
    Assert-ExitCode "restore into drill database"
    Record "restore: ok"

    $tables = @(
        "courses_course",
        "courses_courseoffering",
        "accounts_user",
        "academics_academicterm",
        "students_enrollment",
        "conversations_conversation",
        "notifications_notification"
    )
    $allMatch = $true
    foreach ($table in $tables) {
        $sourceCount = Get-TableCount -Database $sourceDb -Table $table -User $dbUser
        $restoredCount = Get-TableCount -Database $tempDb -Table $table -User $dbUser
        $match = $sourceCount -eq $restoredCount
        if (-not $match) { $allMatch = $false }
        Record ("table {0}: source={1} restored={2} match={3}" -f $table, $sourceCount, $restoredCount, $match)
    }
    if (-not $allMatch) { throw "Restored row counts do not match the source." }

    # Real application query through the backend image against the restored DB.
    $user = Get-RequiredEnv $envMap "POSTGRES_USER"
    $password = Get-RequiredEnv $envMap "POSTGRES_PASSWORD"
    $encodedUser = [uri]::EscapeDataString($user)
    $encodedPassword = [uri]::EscapeDataString($password)
    $restoredUrl = "postgresql://$encodedUser`:$encodedPassword@db:5432/$tempDb"
    $script = "from apps.courses.models import Course; from apps.students.models import Enrollment; from apps.accounts.models import User; print(f'DJANGO courses={Course.objects.count()} users={User.objects.count()} enrollments={Enrollment.objects.count()}')"
    $djangoOutput = (& docker @compose run --rm --no-deps -e "DATABASE_URL=$restoredUrl" backend python manage.py shell -c $script 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $lines.Add(($djangoOutput -join "`n"))
        throw "Django could not query the restored database."
    }
    $djangoLine = ($djangoOutput | Where-Object { $_ -match 'DJANGO ' } | Select-Object -Last 1)
    if (-not $djangoLine) {
        $lines.Add(($djangoOutput -join "`n"))
        throw "Django ORM query against the restored database produced no result."
    }
    Record ($djangoLine.Trim())
    Record "django ORM: ok"

    Record "RESULT: PASS"
    [System.IO.File]::WriteAllText($evidence, ($lines -join "`n"), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Restore drill PASSED. Evidence: $evidence"
} finally {
    try {
        if ($dbUser) {
            & docker @compose exec -T db dropdb -U $dbUser --if-exists $tempDb *> $null
        }
    } catch {
        # Best-effort cleanup; the primary database is unaffected either way.
    }
    Pop-Location
}
