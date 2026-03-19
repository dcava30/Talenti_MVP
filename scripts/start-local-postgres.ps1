param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PostgresUser = "postgres",
    [string]$PostgresPassword = "postgres",
    [string]$PostgresDb = "postgres",
    [string[]]$AdditionalDatabases = @()
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$repoRootResolved = (Resolve-Path $RepoRoot).Path

Write-Section "Start local PostgreSQL"
$env:POSTGRES_USER = $PostgresUser
$env:POSTGRES_PASSWORD = $PostgresPassword
$env:POSTGRES_DB = $PostgresDb
Invoke-Checked "docker" @("compose", "up", "-d", "postgres") $repoRootResolved
Wait-ForComposePostgres -Workdir $repoRootResolved -User $PostgresUser -Database $PostgresDb

foreach ($database in @($PostgresDb) + $AdditionalDatabases) {
    Ensure-ComposePostgresDatabase -Workdir $repoRootResolved -User $PostgresUser -Database $database
}

Write-Host "`nLocal PostgreSQL is ready."
