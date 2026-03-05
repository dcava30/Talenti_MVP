param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ==="
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$CommandArgs,
        [string]$Workdir = ""
    )

    if ($Workdir) {
        Push-Location $Workdir
    }
    try {
        & $Exe @CommandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $Exe $($CommandArgs -join ' ')"
        }
    } finally {
        if ($Workdir) {
            Pop-Location
        }
    }
}

function Wait-ForComposePostgres {
    param(
        [string]$Workdir,
        [string]$User,
        [string]$Database,
        [int]$TimeoutSec = 180
    )
    $start = Get-Date
    while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($TimeoutSec)) {
        Push-Location $Workdir
        try {
            & docker compose exec -T postgres pg_isready -U $User -d $Database *> $null
            if ($LASTEXITCODE -eq 0) {
                return
            }
        } finally {
            Pop-Location
        }
        Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for local PostgreSQL readiness."
}

function Get-DatabaseNameFromUrl {
    param([string]$DatabaseUrl)
    $match = [regex]::Match($DatabaseUrl, "/([^/?]+)(\\?.*)?$")
    if (-not $match.Success) {
        throw "Could not determine database name from URL: $DatabaseUrl"
    }
    return $match.Groups[1].Value
}

function Ensure-ComposePostgresDatabase {
    param(
        [string]$Workdir,
        [string]$User,
        [string]$Database
    )
    $escapedDatabaseForLiteral = $Database.Replace("'", "''")
    $escapedDatabaseForIdentifier = $Database.Replace('"', '""')
    $existsQuery = "SELECT 1 FROM pg_database WHERE datname = '$escapedDatabaseForLiteral';"
    Push-Location $Workdir
    try {
        $exists = & docker compose exec -T postgres psql -U $User -d postgres -tAc $existsQuery
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to query PostgreSQL databases."
        }
        if (-not $exists.Trim()) {
            & docker compose exec -T postgres psql -U $User -d postgres -c "CREATE DATABASE `"$escapedDatabaseForIdentifier`";" *> $null
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create PostgreSQL database '$Database'."
            }
        }
    } finally {
        Pop-Location
    }
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$backendPath = Join-Path $repoRootResolved "backend"
$acsPath = Join-Path $repoRootResolved "python-acs-service"
$modelRunner = Join-Path $repoRootResolved "scripts\run-model-tests.ps1"
$startedLocalPostgres = $false
$originalTestDatabaseUrl = $env:TEST_DATABASE_URL
$backendTestDatabaseUrl = $env:BACKEND_TEST_DATABASE_URL
$acsTestDatabaseUrl = $env:ACS_TEST_DATABASE_URL

foreach ($path in @($backendPath, $acsPath, $modelRunner)) {
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
        Write-Section "Start local PostgreSQL for tests"
        $env:POSTGRES_USER = "postgres"
        $env:POSTGRES_PASSWORD = "postgres"
        $env:POSTGRES_DB = "postgres"
        Invoke-Checked "docker" @("compose", "up", "-d", "postgres") $repoRootResolved
        Wait-ForComposePostgres -Workdir $repoRootResolved -User $env:POSTGRES_USER -Database $env:POSTGRES_DB
        Ensure-ComposePostgresDatabase -Workdir $repoRootResolved -User $env:POSTGRES_USER -Database (Get-DatabaseNameFromUrl $backendTestDatabaseUrl)
        Ensure-ComposePostgresDatabase -Workdir $repoRootResolved -User $env:POSTGRES_USER -Database (Get-DatabaseNameFromUrl $acsTestDatabaseUrl)
        $startedLocalPostgres = $true
    }

    Write-Section "Frontend tests (Vitest)"
    Invoke-Checked "npm.cmd" @("run", "test") $repoRootResolved

    Write-Section "Backend tests (pytest)"
    $env:TEST_DATABASE_URL = $backendTestDatabaseUrl
    Invoke-Checked $PythonExe @("-m", "pytest", "-q", "tests") $backendPath

    Write-Section "Python ACS service tests (pytest)"
    $env:TEST_DATABASE_URL = $acsTestDatabaseUrl
    Invoke-Checked $PythonExe @("-m", "pytest", "-q", "tests") $acsPath

    Write-Section "Model service tests (pytest)"
    & $modelRunner -RepoRoot $repoRootResolved -PythonExe $PythonExe
    if ($LASTEXITCODE -ne 0) {
        throw "Model service tests failed."
    }
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
