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

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$backendPath = Join-Path $repoRootResolved "backend"
$acsPath = Join-Path $repoRootResolved "python-acs-service"
$modelRunner = Join-Path $repoRootResolved "scripts\run-model-tests.ps1"
$startedLocalPostgres = $false

foreach ($path in @($backendPath, $acsPath, $modelRunner)) {
    if (-not (Test-Path $path)) {
        throw "Required path not found: $path"
    }
}

try {
    if (-not $env:TEST_DATABASE_URL) {
        Write-Section "Start local PostgreSQL for tests"
        $env:POSTGRES_USER = "postgres"
        $env:POSTGRES_PASSWORD = "postgres"
        $env:POSTGRES_DB = "talenti_test"
        Invoke-Checked "docker" @("compose", "up", "-d", "postgres") $repoRootResolved
        Wait-ForComposePostgres -Workdir $repoRootResolved -User $env:POSTGRES_USER -Database $env:POSTGRES_DB
        $env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_test"
        $startedLocalPostgres = $true
    }

    Write-Section "Frontend tests (Vitest)"
    Invoke-Checked "npm.cmd" @("run", "test") $repoRootResolved

    Write-Section "Backend tests (pytest)"
    Invoke-Checked $PythonExe @("-m", "pytest", "-q", "tests") $backendPath

    Write-Section "Python ACS service tests (pytest)"
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
}

Write-Host "`nAll test suites passed."
