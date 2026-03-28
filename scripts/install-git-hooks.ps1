param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$hookPath = Join-Path $repoRootResolved ".githooks/pre-commit"

if (-not (Test-Path (Join-Path $repoRootResolved ".git"))) {
    throw "Repo root must contain a .git directory. Received: $repoRootResolved"
}

if (-not (Test-Path $hookPath)) {
    throw "Missing hook file: $hookPath"
}

Push-Location $repoRootResolved
try {
    git config core.hooksPath .githooks | Out-Null
    Write-Host "Configured core.hooksPath=.githooks"

    $hookTracked = $false
    try {
        git ls-files --error-unmatch .githooks/pre-commit 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $hookTracked = $true
        }
    } catch {
        $hookTracked = $false
    }

    if ($hookTracked) {
        git update-index --chmod=+x .githooks/pre-commit 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Could not set executable bit for .githooks/pre-commit (safe to ignore on Windows)."
        }
    }

    Write-Host "Git pre-commit hook installed."
    Write-Host "Hook command: scripts/run-pre-commit.ps1 -Scope staged -Profile fast"
} finally {
    Pop-Location
}
