param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$modelRunner = Join-Path $repoRootResolved "scripts\run-model-tests.ps1"
$backendRunner = Join-Path $repoRootResolved "scripts\run-backend-tests.ps1"
$acsRunner = Join-Path $repoRootResolved "scripts\run-acs-tests.ps1"
$frontendRunner = Join-Path $repoRootResolved "scripts\run-frontend-checks.ps1"
$postgresRunner = Join-Path $repoRootResolved "scripts\start-local-postgres.ps1"
$startedLocalPostgres = $false
$originalTestDatabaseUrl = $env:TEST_DATABASE_URL
$backendTestDatabaseUrl = $env:BACKEND_TEST_DATABASE_URL
$acsTestDatabaseUrl = $env:ACS_TEST_DATABASE_URL

foreach ($path in @($backendRunner, $acsRunner, $frontendRunner, $modelRunner, $postgresRunner)) {
    if (-not (Test-Path $path)) {
        throw "Required path not found: $path"
    }
}

try {
    if (-not $backendTestDatabaseUrl) {
        if ($env:TEST_DATABASE_URL) {
            $backendTestDatabaseUrl = $env:TEST_DATABASE_URL
        } else {
            $backendTestDatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_backend_test"
        }
    }

    if (-not $acsTestDatabaseUrl) {
        if ($env:ACS_TEST_DATABASE_URL) {
            $acsTestDatabaseUrl = $env:ACS_TEST_DATABASE_URL
        } elseif ($env:TEST_DATABASE_URL) {
            throw "When TEST_DATABASE_URL is set, ACS_TEST_DATABASE_URL must also be set to isolate ACS tests."
        } else {
            $acsTestDatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_acs_test"
        }
    }

    if (-not $env:BACKEND_TEST_DATABASE_URL -and -not $env:ACS_TEST_DATABASE_URL -and -not $env:TEST_DATABASE_URL) {
        & $postgresRunner `
            -RepoRoot $repoRootResolved `
            -PostgresUser "postgres" `
            -PostgresPassword "postgres" `
            -PostgresDb "postgres" `
            -AdditionalDatabases @(
                (Get-DatabaseNameFromUrl $backendTestDatabaseUrl),
                (Get-DatabaseNameFromUrl $acsTestDatabaseUrl)
            )
        $startedLocalPostgres = $true
    }

    & $frontendRunner -RepoRoot $repoRootResolved -Mode test
    & $backendRunner -RepoRoot $repoRootResolved -PythonExe $PythonExe -DatabaseUrl $backendTestDatabaseUrl -SkipDatabaseBootstrap
    & $acsRunner -RepoRoot $repoRootResolved -PythonExe $PythonExe -DatabaseUrl $acsTestDatabaseUrl -SkipDatabaseBootstrap
    & $modelRunner -RepoRoot $repoRootResolved -PythonExe $(if ($PythonExe) { $PythonExe } else { "python" })
} finally {
    if ($startedLocalPostgres) {
        try {
            Write-Section "Stop local PostgreSQL for tests"
            Invoke-Checked "docker" @("compose", "stop", "postgres") $repoRootResolved
        } catch {
            Write-Host "Failed to stop local PostgreSQL: $_"
        }
    }

    if ($null -ne $originalTestDatabaseUrl) {
        $env:TEST_DATABASE_URL = $originalTestDatabaseUrl
    } else {
        Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
    }
}

Write-Host "`nAll test suites passed."
