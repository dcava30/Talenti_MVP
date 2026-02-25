param(
    [string]$RepoRoot = (Resolve-Path ".").Path,
    [int]$BackendPort = 8000,
    [int]$Model1Port = 8001,
    [int]$Model2Port = 8002,
    [int]$FrontendPort = 5173,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ==="
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$TimeoutSec = 180
    )
    $start = Get-Date
    while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($TimeoutSec)) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 5
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Timed out waiting for $Url"
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Args,
        [string]$Workdir = ""
    )
    if ($Workdir) {
        Push-Location $Workdir
    }
    try {
        & $Exe @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $Exe $($Args -join ' ')"
        }
    } finally {
        if ($Workdir) {
            Pop-Location
        }
    }
}

function Ensure-Venv {
    param([string]$VenvPath)
    if (-not (Test-Path $VenvPath)) {
        Write-Host "Creating venv at $VenvPath"
        python -m venv $VenvPath
    }
    $pythonExe = Join-Path $VenvPath "Scripts\\python.exe"
    if (-not (Test-Path $pythonExe)) {
        throw "Python executable not found at $pythonExe"
    }
    return $pythonExe
}

function Set-Or-AppendEnvKey {
    param(
        [string]$EnvPath,
        [string]$Key,
        [string]$Value
    )
    if (-not (Test-Path $EnvPath)) {
        New-Item -ItemType File -Path $EnvPath -Force | Out-Null
    }

    $lines = Get-Content $EnvPath -ErrorAction SilentlyContinue
    if ($null -eq $lines) {
        $lines = @()
    }

    $pattern = "^$([regex]::Escape($Key))="
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        $lines += "$Key=$Value"
    }
    Set-Content -Path $EnvPath -Value $lines -Encoding ASCII
}

Write-Section "Prepare environment"
$repoRootResolved = (Resolve-Path $RepoRoot).Path
$envPath = Join-Path $repoRootResolved ".env"
$envExamplePath = Join-Path $repoRootResolved ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
    } else {
        New-Item -ItemType File -Path $envPath -Force | Out-Null
    }
}

$jwtSecret = "dev-" + ([Guid]::NewGuid().ToString("N"))
Set-Or-AppendEnvKey -EnvPath $envPath -Key "VITE_API_BASE_URL" -Value "http://localhost:$BackendPort"
Set-Or-AppendEnvKey -EnvPath $envPath -Key "DATABASE_URL" -Value "sqlite:///./data/app.db"
Set-Or-AppendEnvKey -EnvPath $envPath -Key "JWT_SECRET" -Value $jwtSecret
Set-Or-AppendEnvKey -EnvPath $envPath -Key "ENVIRONMENT" -Value "development"
Set-Or-AppendEnvKey -EnvPath $envPath -Key "ALLOWED_ORIGINS" -Value "[""http://localhost:$FrontendPort""]"
Set-Or-AppendEnvKey -EnvPath $envPath -Key "MODEL_SERVICE_1_URL" -Value "http://localhost:$Model1Port"
Set-Or-AppendEnvKey -EnvPath $envPath -Key "MODEL_SERVICE_2_URL" -Value "http://localhost:$Model2Port"

Write-Section "Bootstrap backend dependencies"
$backendPath = Join-Path $repoRootResolved "backend"
$backendPython = Ensure-Venv (Join-Path $backendPath ".venv")
Invoke-Checked $backendPython @("-m", "pip", "install", "--upgrade", "pip")
$backendDeps = @(
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.30",
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

Write-Section "Bootstrap model-service-1 dependencies"
$ms1Path = Join-Path $repoRootResolved "model-service-1"
$ms1Python = Ensure-Venv (Join-Path $ms1Path ".venv")
Invoke-Checked $ms1Python @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $ms1Python @("-m", "pip", "install", "-r", "requirements.txt") $ms1Path

Write-Section "Bootstrap model-service-2 dependencies"
$ms2Path = Join-Path $repoRootResolved "model-service-2"
$ms2Python = Ensure-Venv (Join-Path $ms2Path ".venv")
Invoke-Checked $ms2Python @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $ms2Python @("-m", "pip", "install", "-r", "requirements.txt") $ms2Path

Write-Section "Install frontend dependencies"
Invoke-Checked "cmd.exe" @("/c", "npm", "install") $repoRootResolved

$logsDir = Join-Path $repoRootResolved "logs\\start-local"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$processes = @()
try {
    Write-Section "Start model-service-1"
    $ms1Proc = Start-Process -FilePath $ms1Python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Model1Port -WorkingDirectory $ms1Path -RedirectStandardOutput (Join-Path $logsDir "model-service-1.out.log") -RedirectStandardError (Join-Path $logsDir "model-service-1.err.log") -PassThru
    $processes += $ms1Proc

    Write-Section "Start model-service-2"
    $ms2Proc = Start-Process -FilePath $ms2Python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Model2Port -WorkingDirectory $ms2Path -RedirectStandardOutput (Join-Path $logsDir "model-service-2.out.log") -RedirectStandardError (Join-Path $logsDir "model-service-2.err.log") -PassThru
    $processes += $ms2Proc

    Write-Section "Start backend"
    $backendProc = Start-Process -FilePath $backendPython -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$BackendPort -WorkingDirectory $backendPath -RedirectStandardOutput (Join-Path $logsDir "backend.out.log") -RedirectStandardError (Join-Path $logsDir "backend.err.log") -PassThru
    $processes += $backendProc

    Write-Section "Start frontend"
    $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c","npm","run","dev","--","--host","127.0.0.1","--port",$FrontendPort -WorkingDirectory $repoRootResolved -RedirectStandardOutput (Join-Path $logsDir "frontend.out.log") -RedirectStandardError (Join-Path $logsDir "frontend.err.log") -PassThru
    $processes += $frontendProc

    Write-Section "Wait for health checks"
    Wait-ForUrl "http://localhost:$Model1Port/health" | Out-Null
    Wait-ForUrl "http://localhost:$Model2Port/health" | Out-Null
    Wait-ForUrl "http://localhost:$BackendPort/health" | Out-Null
    Wait-ForUrl "http://localhost:$FrontendPort" | Out-Null

    Write-Host "Local stack is running."
    Write-Host "Frontend: http://localhost:$FrontendPort"
    Write-Host "Backend:  http://localhost:$BackendPort"

    if ($Detach) {
        Write-Host "Detach mode enabled. Processes left running."
        exit 0
    }

    Write-Host "Press Ctrl+C to stop all services."
    while ($true) {
        Start-Sleep -Seconds 2
    }
} finally {
    if (-not $Detach) {
        Write-Section "Cleanup"
        foreach ($proc in $processes) {
            if ($proc -and -not $proc.HasExited) {
                try {
                    Stop-Process -Id $proc.Id -Force
                } catch {
                    Write-Host "Failed to stop process $($proc.Id): $_"
                }
            }
        }
    }
}
