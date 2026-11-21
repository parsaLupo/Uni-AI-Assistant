# Restore a pg_dump custom-format backup into the local PostgreSQL container.
#
#   # Restore the primary demo database (interactive confirmation + auto backup):
#   scripts/restore.ps1 -BackupFile backups/usa_db_20260101_120000.dump
#
#   # Restore into an isolated database (no confirmation needed):
#   scripts/restore.ps1 -BackupFile backups/x.dump -TargetDatabase usa_db_restore_test -CreateIfMissing
#
# The script refuses a destructive restore of the live database unless the
# operator types the database name or passes -Force, takes a safety backup
# first, and verifies that the restored schema contains the core tables.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [string]$TargetDatabase = "",
    [switch]$Force,
    [switch]$CreateIfMissing,
    [switch]$DropAfter
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$backupPath = if ([IO.Path]::IsPathRooted($BackupFile)) { $BackupFile } else { Join-Path $script:RepoRoot $BackupFile }
if (-not (Test-Path -LiteralPath $backupPath)) { throw "Backup file not found: $backupPath" }

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName
    $dbUser = Get-RequiredEnv (Get-DotEnv (Resolve-EnvPath $EnvFile)) "POSTGRES_USER"

    $sourceDb = "$(& docker @compose exec -T db sh -c 'printf %s "$POSTGRES_DB"')".Trim()
    if (-not $sourceDb) { throw "Could not read POSTGRES_DB from the db container." }
    if ([string]::IsNullOrWhiteSpace($TargetDatabase)) { $TargetDatabase = $sourceDb }

    $isPrimary = $TargetDatabase -eq $sourceDb
    if ($isPrimary) {
        if (-not $Force) {
            Write-Host "WARNING: this replaces the live database '$sourceDb'."
            $answer = Read-Host "Type the database name '$sourceDb' to continue"
            if ($answer -ne $sourceDb) { throw "Restore cancelled: confirmation did not match." }
        }
        Write-Host "Taking a safety backup before changing the primary database..."
        $safety = & "$PSScriptRoot\backup.ps1" -EnvFile $EnvFile -ProjectName $ProjectName
        Write-Host "Safety backup: $safety"

        # Drop app connections so pg_restore --clean can replace objects.
        & docker @compose exec -T db psql -U $dbUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$sourceDb' AND pid <> pg_backend_pid()" *> $null
    }

    $exists = "$(& docker @compose exec -T db psql -U $dbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$TargetDatabase'")".Trim()
    if ($exists -ne "1") {
        if (-not $CreateIfMissing) {
            throw "Database '$TargetDatabase' does not exist. Pass -CreateIfMissing to create it."
        }
        Write-Host "Creating database '$TargetDatabase'..."
        & docker @compose exec -T db createdb -U $dbUser -O $dbUser "$TargetDatabase"
        Assert-ExitCode "createdb"
    }

    $containerPath = "/tmp/usa_restore_$([guid]::NewGuid().ToString('N')).dump"
    & docker @compose cp $backupPath "db:$containerPath"
    Assert-ExitCode "docker compose cp restore"

    Write-Host "Restoring into '$TargetDatabase'..."
    & docker @compose exec -T db pg_restore -U $dbUser -d "$TargetDatabase" --clean --if-exists --no-owner --no-acl --exit-on-error $containerPath
    Assert-ExitCode "pg_restore"
    & docker @compose exec -T db rm -f $containerPath *> $null

    $table = "$(& docker @compose exec -T db psql -U $dbUser -d "$TargetDatabase" -tAc "SELECT to_regclass('public.courses_course') IS NOT NULL")".Trim()
    if ($table -ne "t") { throw "Restore verification failed: courses_course table is missing in '$TargetDatabase'." }
    $courses = "$(& docker @compose exec -T db psql -U $dbUser -d "$TargetDatabase" -tAc "SELECT count(*) FROM courses_course")".Trim()
    $users = "$(& docker @compose exec -T db psql -U $dbUser -d "$TargetDatabase" -tAc "SELECT count(*) FROM accounts_user")".Trim()
    $enrollments = "$(& docker @compose exec -T db psql -U $dbUser -d "$TargetDatabase" -tAc "SELECT count(*) FROM students_enrollment")".Trim()
    Write-Host "Verified '$TargetDatabase': courses=$courses users=$users enrollments=$enrollments"

    if ($DropAfter) {
        if ($isPrimary) { throw "Refusing to drop the primary database. Drop was ignored." }
        Write-Host "Dropping temporary database '$TargetDatabase'..."
        & docker @compose exec -T db dropdb -U $dbUser --if-exists "$TargetDatabase"
        Assert-ExitCode "dropdb"
    }
} finally {
    Pop-Location
}
