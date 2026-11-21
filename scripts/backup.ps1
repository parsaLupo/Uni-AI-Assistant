# Create a PostgreSQL-native backup outside the container filesystem.
#
#   scripts/backup.ps1
#   scripts/backup.ps1 -OutDir D:\Backups\usa
#
# Uses pg_dump's custom format inside the `db` container, copies it to the host,
# and verifies the archive with pg_restore --list before keeping it. Credentials
# come from the container environment; no password is printed or passed on a
# command line. Old files are pruned by BACKUP_RETENTION_DAYS (default 14).
[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [string]$OutDir = "backups"
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$envPath = Resolve-EnvPath $EnvFile
$envMap = Get-DotEnv $envPath
$retentionDays = if ($envMap["BACKUP_RETENTION_DAYS"]) { [int]$envMap["BACKUP_RETENTION_DAYS"] } else { 14 }

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName
    $destinationDir = if ([IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $script:RepoRoot $OutDir }
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null

    & docker @compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' *> $null
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL is not running. Start it with: docker compose up -d db" }

    $dbName = "$(& docker @compose exec -T db sh -c 'printf %s "$POSTGRES_DB"')".Trim()
    if (-not $dbName) { throw "Could not read POSTGRES_DB from the db container." }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $containerPath = "/tmp/usa_backup_$stamp.dump"
    $hostPath = Join-Path $destinationDir "${dbName}_$stamp.dump"

    Write-Host "Creating backup of '$dbName'..."
    & docker @compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file "$1"' sh $containerPath
    Assert-ExitCode "pg_dump"

    & docker @compose exec -T db pg_restore --list $containerPath *> $null
    if ($LASTEXITCODE -ne 0) { throw "Backup archive failed pg_restore --list validation." }

    & docker @compose cp "db:$containerPath" "$hostPath"
    Assert-ExitCode "docker compose cp backup"
    & docker @compose exec -T db rm -f $containerPath *> $null

    $sizeMb = [math]::Round((Get-Item -LiteralPath $hostPath).Length / 1MB, 2)
    Write-Host "Backup verified: $hostPath ($sizeMb MB)"

    if ($retentionDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-$retentionDays)
        $expired = Get-ChildItem -LiteralPath $destinationDir -Filter "*.dump" |
            Where-Object { $_.LastWriteTime -lt $cutoff }
        foreach ($file in $expired) {
            Write-Host "Retention: removing $($file.Name) (older than $retentionDays days)"
            Remove-Item -LiteralPath $file.FullName -Force
        }
    }

    Write-Output $hostPath
} finally {
    Pop-Location
}
