param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = "",
    [string]$DatabaseUrl = "",
    [switch]$SkipDatabaseBootstrap
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$acsPath = Join-Path $repoRootResolved "python-acs-service"

if (-not $DatabaseUrl) {
    $DatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_acs_test"
}

if (-not $SkipDatabaseBootstrap) {
    $databaseName = Get-DatabaseNameFromUrl $DatabaseUrl
    & (Join-Path $PSScriptRoot "start-local-postgres.ps1") `
        -RepoRoot $repoRootResolved `
        -PostgresUser "postgres" `
        -PostgresPassword "postgres" `
        -PostgresDb "postgres" `
        -AdditionalDatabases @($databaseName)
}

$resolvedPython = if ($PythonExe) { $PythonExe } else { Resolve-PythonCommand -RepoPath $acsPath }

Write-Section "Python ACS service tests (pytest)"
$originalTestDatabaseUrl = $env:TEST_DATABASE_URL
try {
    $env:TEST_DATABASE_URL = $DatabaseUrl
    Invoke-Checked $resolvedPython @("-m", "pytest", "-q", "tests") $acsPath
} finally {
    if ($null -ne $originalTestDatabaseUrl) {
        $env:TEST_DATABASE_URL = $originalTestDatabaseUrl
    } else {
        Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
    }
}

Write-Host "`nACS service tests passed."
