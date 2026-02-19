param(
    [ValidateSet("docker", "local")]
    [string]$Mode = "docker",
    [string]$BackendUrl = "http://localhost:8000",
    [string]$Model1Url = "http://localhost:8001",
    [string]$Model2Url = "http://localhost:8002",
    [string]$JwtSecret = "",
    [int]$TimeoutSeconds = 180,
    [switch]$KeepRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ==="
}

function Wait-Healthy {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 5 | Out-Null
            Write-Host "$Name healthy at $Url"
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "$Name did not become healthy at $Url within $TimeoutSeconds seconds."
}

function Get-ComposeCommand {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            docker compose version | Out-Null
            return "docker compose"
        } catch {
        }
    }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        return "docker-compose"
    }
    throw "Docker Compose not found. Install Docker Desktop or use -Mode local."
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body,
        [hashtable]$Headers = @{}
    )
    $json = $null
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 8
    }
    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -Body $json -ContentType "application/json"
}

if (-not (Test-Path (Join-Path $RepoRoot "model-service-1"))) {
    throw "Missing model-service-1 directory. Clone or add the model service before running this test."
}
if (-not (Test-Path (Join-Path $RepoRoot "model-service-2"))) {
    throw "Missing model-service-2 directory. Clone or add the model service before running this test."
}

$composeCommand = $null
$backendProc = $null
$model1Proc = $null
$model2Proc = $null

try {
    if ($Mode -eq "docker") {
        $composeCommand = Get-ComposeCommand
        if (-not $JwtSecret) {
            $JwtSecret = [Guid]::NewGuid().ToString("N")
        }

        $overridePath = Join-Path $env:TEMP ("talenti-compose.jwt.{0}.yml" -f ([Guid]::NewGuid().ToString("N")))
        @"
services:
  backend:
    environment:
      - JWT_SECRET=$JwtSecret
"@ | Set-Content -Path $overridePath -Encoding UTF8

        Write-Section "Starting services via Docker Compose"
        if ($composeCommand -eq "docker compose") {
            docker compose -f docker-compose.yml -f $overridePath up -d --build backend model-service-1 model-service-2
        } else {
            docker-compose -f docker-compose.yml -f $overridePath up -d --build backend model-service-1 model-service-2
        }

        Remove-Item $overridePath -ErrorAction SilentlyContinue
    } elseif ($Mode -eq "local") {
        if (-not $JwtSecret) {
            $JwtSecret = "dev-secret"
        }

        Write-Section "Starting services locally"
        $env:MODEL_SERVICE_1_URL = $Model1Url
        $env:MODEL_SERVICE_2_URL = $Model2Url
        $env:JWT_SECRET = $JwtSecret
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = "sqlite:///./data/app.db"
        }

        $model1Proc = Start-Process -FilePath "python" -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8001", "--workers", "1"
        ) -WorkingDirectory (Join-Path $RepoRoot "model-service-1") -PassThru

        $model2Proc = Start-Process -FilePath "python" -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8002", "--workers", "1"
        ) -WorkingDirectory (Join-Path $RepoRoot "model-service-2") -PassThru

        $backendProc = Start-Process -FilePath "python" -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000", "--workers", "1"
        ) -WorkingDirectory (Join-Path $RepoRoot "backend") -PassThru
    }

    Write-Section "Waiting for health checks"
    Wait-Healthy -Name "Model service 1" -Url "$Model1Url/health" -TimeoutSeconds $TimeoutSeconds
    Wait-Healthy -Name "Model service 2" -Url "$Model2Url/health" -TimeoutSeconds $TimeoutSeconds
    Wait-Healthy -Name "Backend" -Url "$BackendUrl/health" -TimeoutSeconds $TimeoutSeconds

    Write-Section "Register and login"
    $email = "test+{0}@example.com" -f ([Guid]::NewGuid().ToString("N").Substring(0, 8))
    $password = "Test1234!"
    $registerBody = @{
        email = $email
        password = $password
        full_name = "Model Test User"
    }
    try {
        Invoke-Json -Method "Post" -Url "$BackendUrl/api/auth/register" -Body $registerBody | Out-Null
    } catch {
        Write-Host "Register failed (may already exist). Continuing to login."
    }

    $loginBody = @{
        email = $email
        password = $password
    }
    $loginResponse = Invoke-Json -Method "Post" -Url "$BackendUrl/api/auth/login" -Body $loginBody
    if (-not $loginResponse.access_token) {
        throw "Login failed. No access token returned."
    }
    $token = $loginResponse.access_token

    Write-Section "Calling scoring endpoint"
    $scoreBody = @{
        interview_id = "test-" + ([Guid]::NewGuid().ToString("N").Substring(0, 8))
        transcript = @(
            @{ speaker = "interviewer"; content = "Tell me about yourself." },
            @{ speaker = "candidate"; content = "I have 5 years of experience in software development and love solving problems." }
        )
        job_description = "We are hiring a Python engineer with FastAPI experience and cloud exposure (Azure preferred)."
        resume_text = "Built FastAPI services in Python, deployed to Azure App Service, and worked with SQL databases."
        role_title = "Software Engineer"
        seniority = "mid"
        rubric = @{
            communication = 0.3
            technical = 0.4
            problem_solving = 0.3
        }
    }
    $headers = @{ Authorization = "Bearer $token" }
    $scoreResponse = Invoke-Json -Method "Post" -Url "$BackendUrl/api/v1/scoring/analyze" -Body $scoreBody -Headers $headers

    Write-Section "Scoring response"
    $scoreResponse | ConvertTo-Json -Depth 10 | Write-Host
    Write-Host "Test completed successfully."
} finally {
    if (-not $KeepRunning) {
        if ($Mode -eq "docker" -and $composeCommand) {
            Write-Section "Stopping Docker Compose services"
            if ($composeCommand -eq "docker compose") {
                docker compose -f docker-compose.yml down
            } else {
                docker-compose -f docker-compose.yml down
            }
        }

        if ($Mode -eq "local") {
            Write-Section "Stopping local processes"
            foreach ($proc in @($backendProc, $model1Proc, $model2Proc)) {
                if ($null -ne $proc -and -not $proc.HasExited) {
                    try {
                        Stop-Process -Id $proc.Id -Force
                    } catch {
                    }
                }
            }
        }
    }
}
