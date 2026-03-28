param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$DisableHooksIfShBroken = $true
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
    $shCandidates = New-Object System.Collections.Generic.List[string]
    $shCommand = Get-Command "sh.exe" -ErrorAction SilentlyContinue
    if ($shCommand) {
        $shCandidates.Add($shCommand.Source)
    }
    $shCommand = Get-Command "sh" -ErrorAction SilentlyContinue
    if ($shCommand) {
        $shCandidates.Add($shCommand.Source)
    }

    $gitCommand = Get-Command "git" -ErrorAction SilentlyContinue
    if ($gitCommand) {
        $gitBinPath = Split-Path $gitCommand.Source -Parent
        $gitRootPath = Resolve-Path (Join-Path $gitBinPath "..")
        $gitShPath = Join-Path $gitRootPath "usr\bin\sh.exe"
        if (Test-Path $gitShPath) {
            $shCandidates.Add((Resolve-Path $gitShPath).Path)
        }
    }

    $shCandidates = @($shCandidates | Select-Object -Unique)
    foreach ($shPath in $shCandidates) {
        $shHealthy = $true
        try {
            & $shPath -lc "exit 0" *> $null
            if ($LASTEXITCODE -ne 0) {
                $shHealthy = $false
            }
        } catch {
            $shHealthy = $false
        }

        if (-not $shHealthy -and $DisableHooksIfShBroken) {
            $disabledHooksPath = ".githooks-disabled"
            $disabledHooksFullPath = Join-Path $repoRootResolved $disabledHooksPath
            if (-not (Test-Path $disabledHooksFullPath)) {
                New-Item -ItemType Directory -Path $disabledHooksFullPath -Force | Out-Null
            }
            git config core.hooksPath $disabledHooksPath | Out-Null
            Write-Host "Detected broken Git shell runtime (`sh`) at: $shPath"
            Write-Host "Configured core.hooksPath=$disabledHooksPath to avoid commit failures."
            Write-Host 'Run `npm run precommit` manually before committing while Git shell is repaired.'
            return
        }
    }

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
