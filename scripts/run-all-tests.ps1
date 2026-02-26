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

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$backendPath = Join-Path $repoRootResolved "backend"
$acsPath = Join-Path $repoRootResolved "python-acs-service"
$modelRunner = Join-Path $repoRootResolved "scripts\run-model-tests.ps1"

foreach ($path in @($backendPath, $acsPath, $modelRunner)) {
    if (-not (Test-Path $path)) {
        throw "Required path not found: $path"
    }
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

Write-Host "`nAll test suites passed."
