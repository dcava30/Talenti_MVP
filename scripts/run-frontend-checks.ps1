param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("lint", "test", "build", "dev", "all")]
    [string]$Mode = "all",
    [string]$ApiBaseUrl = "http://localhost:8000",
    [int]$FrontendPort = 5173,
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$nodeModulesPath = Join-Path $repoRootResolved "node_modules"

if ($InstallDependencies -or -not (Test-Path $nodeModulesPath)) {
    Write-Section "Install frontend dependencies"
    Invoke-Checked "cmd.exe" @("/c", "npm", "install") $repoRootResolved
}

$env:VITE_API_BASE_URL = $ApiBaseUrl

switch ($Mode) {
    "lint" {
        Write-Section "Frontend lint"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "lint") $repoRootResolved
    }
    "test" {
        Write-Section "Frontend tests (Vitest)"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "test") $repoRootResolved
    }
    "build" {
        Write-Section "Frontend build"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "build") $repoRootResolved
    }
    "dev" {
        Write-Section "Frontend dev server"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort") $repoRootResolved
    }
    "all" {
        Write-Section "Frontend lint"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "lint") $repoRootResolved
        Write-Section "Frontend tests (Vitest)"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "test") $repoRootResolved
        Write-Section "Frontend build"
        Invoke-Checked "cmd.exe" @("/c", "npm", "run", "build") $repoRootResolved
    }
}

Write-Host "`nFrontend $Mode workflow completed."
