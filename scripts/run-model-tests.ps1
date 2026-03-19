param(
    [string]$RepoRoot = (Resolve-Path ".").Path,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$services = @("model-service-1", "model-service-2")

foreach ($svc in $services) {
    $path = Join-Path $RepoRoot $svc
    if (-not (Test-Path $path)) {
        throw "Missing service directory: $path"
    }

    $resolvedPython = $PythonExe
    $venvPython = Join-Path $path ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $resolvedPython = $venvPython
    }

    Write-Host "Running tests in $svc..."
    Push-Location $path
    try {
        & $resolvedPython -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed in $svc"
        }
    } finally {
        Pop-Location
    }
}

Write-Host "All model service tests passed."
