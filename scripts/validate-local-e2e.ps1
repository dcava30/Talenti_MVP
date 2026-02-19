param(
    [string]$RepoRoot = (Resolve-Path ".").Path,
    [int]$BackendPort = 8000,
    [int]$Model1Port = 8001,
    [int]$Model2Port = 8002,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ==="
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$TimeoutSec = 120
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
        [string[]]$Args
    )
    & $Exe @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Exe $($Args -join ' ')"
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

Write-Section "Prepare env"
$logsDir = Join-Path $RepoRoot "logs\\local-e2e"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$jwt = "dev-" + ([guid]::NewGuid().ToString("N"))
$envContent = @"
VITE_API_BASE_URL=http://localhost:$BackendPort
DATABASE_URL=sqlite:///./data/app.db
JWT_SECRET=$jwt
ENVIRONMENT=development
ALLOWED_ORIGINS=[""http://localhost:$FrontendPort""]
MODEL_SERVICE_1_URL=http://localhost:$Model1Port
MODEL_SERVICE_2_URL=http://localhost:$Model2Port
"@
Set-Content -Path (Join-Path $RepoRoot ".env") -Encoding ASCII -Value $envContent
Set-Content -Path (Join-Path $RepoRoot "backend\\.env") -Encoding ASCII -Value $envContent

Write-Section "Set up backend venv"
$backendPath = Join-Path $RepoRoot "backend"
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

Write-Section "Set up model-service-1 venv"
$ms1Path = Join-Path $RepoRoot "model-service-1"
$ms1Python = Ensure-Venv (Join-Path $ms1Path ".venv")
Invoke-Checked $ms1Python @("-m", "pip", "install", "--upgrade", "pip")
Push-Location $ms1Path
Invoke-Checked $ms1Python @("-m", "pip", "install", "-r", "requirements.txt")
Pop-Location

Write-Section "Set up model-service-2 venv"
$ms2Path = Join-Path $RepoRoot "model-service-2"
$ms2Python = Ensure-Venv (Join-Path $ms2Path ".venv")
Invoke-Checked $ms2Python @("-m", "pip", "install", "--upgrade", "pip")
Push-Location $ms2Path
Invoke-Checked $ms2Python @("-m", "pip", "install", "-r", "requirements.txt")
Pop-Location

Write-Section "Install frontend dependencies"
Push-Location $RepoRoot
Invoke-Checked "cmd.exe" @("/c", "npm", "install")
Pop-Location

$processes = @()
try {
    Write-Section "Start model services"
    $ms1Out = Join-Path $logsDir "model-service-1.out.log"
    $ms1Err = Join-Path $logsDir "model-service-1.err.log"
    $ms1Proc = Start-Process -FilePath $ms1Python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Model1Port -WorkingDirectory $ms1Path -RedirectStandardOutput $ms1Out -RedirectStandardError $ms1Err -PassThru
    $processes += $ms1Proc

    $ms2Out = Join-Path $logsDir "model-service-2.out.log"
    $ms2Err = Join-Path $logsDir "model-service-2.err.log"
    $ms2Proc = Start-Process -FilePath $ms2Python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Model2Port -WorkingDirectory $ms2Path -RedirectStandardOutput $ms2Out -RedirectStandardError $ms2Err -PassThru
    $processes += $ms2Proc

    Write-Section "Start backend"
    $backendOut = Join-Path $logsDir "backend.out.log"
    $backendErr = Join-Path $logsDir "backend.err.log"
    $backendProc = Start-Process -FilePath $backendPython -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$BackendPort -WorkingDirectory $backendPath -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
    $processes += $backendProc

    Write-Section "Start frontend"
    $frontendOut = Join-Path $logsDir "frontend.out.log"
    $frontendErr = Join-Path $logsDir "frontend.err.log"
    $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c","npm","run","dev","--","--host","127.0.0.1","--port",$FrontendPort -WorkingDirectory $RepoRoot -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
    $processes += $frontendProc

    Write-Section "Wait for health checks"
    Wait-ForUrl "http://localhost:$Model1Port/health" 180 | Out-Null
    Wait-ForUrl "http://localhost:$Model2Port/health" 180 | Out-Null
    Wait-ForUrl "http://localhost:$BackendPort/health" 180 | Out-Null
    Wait-ForUrl "http://localhost:$FrontendPort" 180 | Out-Null

    Write-Section "Run end-to-end interview flow"
    $base = "http://localhost:$BackendPort"
    $email = "e2e+" + ([guid]::NewGuid().ToString("N")) + "@example.com"
    $password = "Test1234!"

    $register = @{
        email = $email
        password = $password
        full_name = "E2E Tester"
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$base/api/auth/register" -Body $register -ContentType "application/json" | Out-Null

    $login = @{
        email = $email
        password = $password
    } | ConvertTo-Json
    $tokenResp = Invoke-RestMethod -Method Post -Uri "$base/api/auth/login" -Body $login -ContentType "application/json"
    $token = $tokenResp.access_token
    $headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

    $orgPayload = @{
        name = "Sample Org"
        description = "E2E validation org"
        industry = "Software"
        website = "https://example.com"
    } | ConvertTo-Json
    $org = Invoke-RestMethod -Method Post -Uri "$base/api/orgs" -Headers $headers -Body $orgPayload

    $jdPath = Join-Path $RepoRoot "model-service-2\\ML engineer JD.txt"
    $resumePath = Join-Path $RepoRoot "model-service-2\\resume.txt"
    $jobDescription = Get-Content -Raw $jdPath
    $resumeText = Get-Content -Raw $resumePath

    $rolePayload = @{
        organisation_id = $org.id
        title = "ML Engineer"
        description = $jobDescription
        department = "Engineering"
        location = "Remote"
        work_type = "Remote"
        employment_type = "Full-time"
    } | ConvertTo-Json -Depth 6
    $role = Invoke-RestMethod -Method Post -Uri "$base/api/roles" -Headers $headers -Body $rolePayload

    $questions = @(
        "Tell me about your Python experience.",
        "Describe an end-to-end ML system you built.",
        "What is your experience with speech-to-text and LLMs?",
        "How do you deploy ML systems in production?"
    )

    $interviewStructure = ($questions | ConvertTo-Json -Depth 4)
    $roleUpdate = @{
        requirements = $jobDescription
        interview_structure = $interviewStructure
        status = "open"
    } | ConvertTo-Json -Depth 6
    Invoke-RestMethod -Method Patch -Uri "$base/api/roles/$($role.id)" -Headers $headers -Body $roleUpdate | Out-Null

    $profilePayload = @{
        first_name = "Sample"
        last_name = "Candidate"
        email = $email
    } | ConvertTo-Json
    $profile = Invoke-RestMethod -Method Post -Uri "$base/api/v1/candidates/profile" -Headers $headers -Body $profilePayload

    $parsePayload = @{
        candidate_id = $profile.user_id
        resume_text = $resumeText
    } | ConvertTo-Json -Depth 6
    Invoke-RestMethod -Method Post -Uri "$base/api/v1/candidates/parse-resume" -Headers $headers -Body $parsePayload | Out-Null

    $appPayload = @{
        job_role_id = $role.id
        candidate_profile_id = $profile.id
        status = "applied"
        source = "e2e"
    } | ConvertTo-Json
    $application = Invoke-RestMethod -Method Post -Uri "$base/api/v1/applications" -Headers $headers -Body $appPayload

    $interviewPayload = @{
        application_id = $application.id
        status = "in_progress"
    } | ConvertTo-Json
    $interview = Invoke-RestMethod -Method Post -Uri "$base/api/v1/interviews" -Headers $headers -Body $interviewPayload

    $answers = @(
        "I have 6 years of Python experience and built multiple FastAPI services.",
        "I designed and deployed an ML pipeline for ranking and summarization using LLMs.",
        "I used Whisper for speech-to-text and built LLM apps with OpenAI APIs.",
        "I deploy with Docker and Kubernetes and set up CI/CD for model serving."
    )

    $transcript = @()
    for ($i = 0; $i -lt $questions.Count; $i++) {
        $transcript += @{ speaker = "interviewer"; content = $questions[$i] }
        $transcript += @{ speaker = "candidate"; content = $answers[$i] }
    }

    foreach ($segment in $transcript) {
        $segmentPayload = $segment | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$base/api/v1/interviews/$($interview.id)/transcripts" -Headers $headers -Body $segmentPayload | Out-Null
    }

    $scorePayload = @{
        interview_id = $interview.id
        transcript = $transcript
        job_description = $jobDescription
        resume_text = $resumeText
        role_title = "ML Engineer"
        seniority = "senior"
    } | ConvertTo-Json -Depth 8
    $score = Invoke-RestMethod -Method Post -Uri "$base/api/v1/scoring/analyze" -Headers $headers -Body $scorePayload

    $savePayload = @{
        interview_id = $interview.id
        overall_score = $score.overall_score
        narrative_summary = $score.summary
        candidate_feedback = $score.summary
        dimensions = $score.dimensions
    } | ConvertTo-Json -Depth 8
    Invoke-RestMethod -Method Post -Uri "$base/api/v1/interviews/$($interview.id)/scores" -Headers $headers -Body $savePayload | Out-Null

    $report = Invoke-RestMethod -Method Get -Uri "$base/api/v1/interviews/$($interview.id)/report" -Headers $headers

    if (-not $report.score) {
        throw "Interview report missing score"
    }
    if (-not $report.dimensions -or $report.dimensions.Count -eq 0) {
        throw "Interview report missing dimensions"
    }

    Write-Host "E2E validation succeeded. Overall score: $($report.score.overall_score)"
} finally {
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
