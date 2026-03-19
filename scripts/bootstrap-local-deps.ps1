param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = "python",
    [switch]$SkipFrontendInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$envPath = Join-Path $repoRootResolved ".env"
$envExamplePath = Join-Path $repoRootResolved ".env.example"

Write-Section "Prepare root env file"
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
    } else {
        New-Item -ItemType File -Path $envPath -Force | Out-Null
    }
}

Write-Section "Bootstrap backend dependencies"
$backendPath = Join-Path $repoRootResolved "backend"
$backendPython = Ensure-Venv -VenvPath (Join-Path $backendPath ".venv") -PythonExe $PythonExe
Invoke-Checked $backendPython @("-m", "pip", "install", "--upgrade", "pip")
$backendDeps = @(
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.30",
    "psycopg[binary]>=3.2.0",
    "alembic>=1.13.1",
    "pydantic>=2.8.2",
    "pydantic-settings>=2.4.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "email-validator>=2.1.0",
    "azure-identity>=1.16.0",
    "azure-storage-blob>=12.20.0",
    "azure-communication-identity>=1.3.0",
    "openai>=1.35.0"
)
Invoke-Checked $backendPython (@("-m", "pip", "install") + $backendDeps)

Write-Section "Bootstrap acs-worker dependencies"
$acsWorkerPath = Join-Path $repoRootResolved "python-acs-service"
$acsWorkerPython = Ensure-Venv -VenvPath (Join-Path $acsWorkerPath ".venv") -PythonExe $PythonExe
Invoke-Checked $acsWorkerPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $acsWorkerPython @("-m", "pip", "install", "-r", "requirements.txt") $acsWorkerPath

Write-Section "Bootstrap model-service-1 dependencies"
$ms1Path = Join-Path $repoRootResolved "model-service-1"
Require-RepoDirectory -Path $ms1Path -Label "model-service-1"
$ms1Python = Ensure-Venv -VenvPath (Join-Path $ms1Path ".venv") -PythonExe $PythonExe
Invoke-Checked $ms1Python @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $ms1Python @("-m", "pip", "install", "-r", "requirements.txt") $ms1Path

Write-Section "Bootstrap model-service-2 dependencies"
$ms2Path = Join-Path $repoRootResolved "model-service-2"
Require-RepoDirectory -Path $ms2Path -Label "model-service-2"
$ms2Python = Ensure-Venv -VenvPath (Join-Path $ms2Path ".venv") -PythonExe $PythonExe
Invoke-Checked $ms2Python @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $ms2Python @("-m", "pip", "install", "-r", "requirements.txt") $ms2Path

if (-not $SkipFrontendInstall) {
    Write-Section "Install frontend dependencies"
    Invoke-Checked "cmd.exe" @("/c", "npm", "install") $repoRootResolved
}

Write-Host "`nLocal dependency bootstrap is ready."
