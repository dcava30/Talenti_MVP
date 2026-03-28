param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("staged", "all")]
    [string]$Scope = "staged",
    [ValidateSet("fast", "full")]
    [string]$Profile = "fast",
    [string]$BackendDatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_backend_test",
    [string]$AcsDatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_acs_test",
    [switch]$SkipDatabaseBootstrap,
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local-common.ps1")

$script:CurrentStepName = ""
$script:PreCommitLogPath = ""

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-ChangedFiles {
    param(
        [string]$RepoPath,
        [ValidateSet("staged", "all")]
        [string]$Selection
    )

    if ($Selection -eq "all") {
        Push-Location $RepoPath
        try {
            return @(git ls-files)
        } finally {
            Pop-Location
        }
    }

    Push-Location $RepoPath
    try {
        return @(git diff --cached --name-only --diff-filter=ACMR)
    } finally {
        Pop-Location
    }
}

function Has-PathMatch {
    param(
        [string[]]$Files,
        [string[]]$Prefixes = @(),
        [string[]]$Exact = @()
    )

    foreach ($file in $Files) {
        if ($Exact -contains $file) {
            return $true
        }
        foreach ($prefix in $Prefixes) {
            if ($file.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        }
    }

    return $false
}

function Enter-Step {
    param([string]$StepName)
    $script:CurrentStepName = $StepName
    Write-Section $StepName
}

function Get-StepWhy {
    param([string]$StepName)

    switch -Regex ($StepName) {
        "^Detect changed files$" { return "Changed-file detection determines which component gates must run for CI parity." }
        "^Install frontend dependencies$" { return "Frontend dependency install ensures lint, tests, and build run against the exact lockfile state used in CI." }
        "^Frontend lint$" { return "Lint failures indicate code-style or static-analysis violations that would fail `pr-fast-quality`." }
        "^Frontend tests$" { return "Frontend test failures indicate behavior regressions that block `pr-fast-quality`." }
        "^Frontend build$" { return "Build failures indicate compile or bundling issues that block deployment readiness." }
        "^Backend dependencies$" { return "Backend dependency setup must succeed for tests and migration checks to match CI." }
        "^Backend tests with CI coverage threshold$" { return "Backend tests must pass with the same coverage gate used in `pr-fast-quality`." }
        "^Backend migration execution check$" { return "Migration execution must succeed to prove schema updates are runnable before merge." }
        "^ACS dependencies$" { return "ACS dependency setup must succeed for test parity with CI." }
        "^ACS tests with CI coverage threshold$" { return "ACS tests must pass with the same coverage gate used in `pr-fast-quality`." }
        "^Start local PostgreSQL test dependencies$" { return "Database-backed gates require local PostgreSQL to be available and initialized." }
        "^Secrets scan \\(gitleaks\\)$" { return "Secret scanning blocks commits that would expose credentials or tokens in source control." }
        "^NPM dependency audit$" { return "NPM audit enforces the same high/critical vulnerability bar as `pr-security-iac`." }
        "^Backend pip-audit$" { return "Backend dependency audit blocks known vulnerable Python packages." }
        "^ACS pip-audit$" { return "ACS dependency audit blocks known vulnerable Python packages." }
        "^Dockerfile lint \\(hadolint\\)$" { return "Dockerfile lint enforces container best practices expected by CI security checks." }
        "^Build local images for vulnerability scan$" { return "Image build failures indicate broken container build inputs that would fail downstream workflows." }
        "^Image vulnerability scan \\(trivy\\)$" { return "Trivy enforces high/critical container vulnerability gates similar to `pr-security-iac`." }
        "^Bicep compile validation$" { return "Bicep compile checks prevent invalid infra templates from reaching deployment workflows." }
        "^IaC policy scan \\(checkov\\)$" { return "IaC policy scanning blocks insecure infrastructure configurations before PR merge." }
        default { return "This step is part of the local CI parity gate and must pass before commit." }
    }
}

function Get-ResolutionHints {
    param(
        [string]$StepName,
        [string]$ErrorMessage
    )

    $hints = New-Object System.Collections.Generic.List[string]

    switch -Regex ($StepName) {
        "^Detect changed files$" {
            $hints.Add("Ensure Git is installed and available on PATH, then retry the commit.")
            $hints.Add("Run `git status` to confirm the repository is healthy and staged changes are visible.")
        }
        "^Install frontend dependencies$" {
            $hints.Add("Run `npm ci` manually and resolve lockfile or registry errors.")
            $hints.Add("If `package-lock.json` changed unexpectedly, regenerate it intentionally and re-run checks.")
        }
        "^Frontend lint$" {
            $hints.Add("Run `npm run lint` and fix the file/rule violations reported.")
            $hints.Add("If a rule should change, update ESLint config in a separate intentional commit.")
        }
        "^Frontend tests$" {
            $hints.Add("Run `npm run test` and fix failing assertions, mocks, or test setup issues.")
            $hints.Add("For intentional behavior changes, update affected tests with the new expected behavior.")
        }
        "^Frontend build$" {
            $hints.Add("Run `npm run build` and resolve TypeScript/transpile/import errors shown in output.")
            $hints.Add("Check unresolved environment variables and stale imports for renamed files.")
        }
        "^Backend tests with CI coverage threshold$" {
            $hints.Add("Run backend tests locally and fix failing tests first.")
            $hints.Add("If coverage is below 70%, add focused tests for changed code paths until the threshold is met.")
        }
        "^Backend migration execution check$" {
            $hints.Add("Run `python backend/scripts/run_migrations.py` with the same `DATABASE_URL` and inspect migration traceback.")
            $hints.Add("Ensure new Alembic revisions are ordered correctly and migration scripts are idempotent.")
        }
        "^ACS tests with CI coverage threshold$" {
            $hints.Add("Run ACS tests locally and fix failures before re-running pre-commit.")
            $hints.Add("If coverage is below 65%, add tests for the changed ACS modules.")
        }
        "^Start local PostgreSQL test dependencies$" {
            $hints.Add("Start Docker Desktop and verify `docker compose up -d postgres` succeeds.")
            $hints.Add("Check that port `5432` is not occupied by another local Postgres instance.")
        }
        "^Secrets scan \\(gitleaks\\)$" {
            $hints.Add("Remove committed secrets and rotate exposed credentials immediately.")
            $hints.Add("If a finding is false positive, add a targeted allow rule with justification.")
        }
        "^NPM dependency audit$" {
            $hints.Add("Run `npm audit --audit-level=high` and patch/upgrade vulnerable dependencies.")
            $hints.Add("Use `npm audit fix` cautiously, then verify app behavior and lockfile consistency.")
        }
        "^Backend pip-audit$" {
            $hints.Add("Upgrade or pin vulnerable Python packages in backend dependencies.")
            $hints.Add("If no direct upgrade exists, document the risk and introduce compensating controls before merge.")
        }
        "^ACS pip-audit$" {
            $hints.Add("Upgrade or pin vulnerable Python packages in `python-acs-service/requirements.txt`.")
            $hints.Add("Re-run audit after dependency changes to confirm the vulnerability is cleared.")
        }
        "^Dockerfile lint \\(hadolint\\)$" {
            $hints.Add("Apply hadolint suggestions in the reported Dockerfile lines.")
            $hints.Add("If an exception is necessary, add a specific inline ignore with rationale.")
        }
        "^Build local images for vulnerability scan$" {
            $hints.Add("Run `docker build` for the failing image and fix Dockerfile/context path issues.")
            $hints.Add("Confirm required build files are tracked and not excluded by `.dockerignore`.")
        }
        "^Image vulnerability scan \\(trivy\\)$" {
            $hints.Add("Update base images and vulnerable packages, then rebuild and re-scan.")
            $hints.Add("Prioritize HIGH/CRITICAL findings and remove unused vulnerable packages where possible.")
        }
        "^Bicep compile validation$" {
            $hints.Add("Run `az bicep build --file <path>` for the failing template and fix syntax or module references.")
            $hints.Add("Ensure all parameter names and template references match across environments.")
        }
        "^IaC policy scan \\(checkov\\)$" {
            $hints.Add("Review failing Checkov policies and remediate the insecure configuration.")
            $hints.Add("If suppression is needed, scope it narrowly and include explicit security justification.")
        }
    }

    if ($ErrorMessage -match "Required command not found: docker") {
        $hints.Add("Install Docker Desktop and ensure the Docker daemon is running.")
    }
    if ($ErrorMessage -match "Required command not found: az") {
        $hints.Add("Install Azure CLI and run `az login` before infra checks.")
    }
    if ($ErrorMessage -match "The term 'git' is not recognized") {
        $hints.Add("Install Git and ensure `git` is available from the current shell.")
    }
    if ($ErrorMessage -match "cov-fail-under=70") {
        $hints.Add("Coverage gate failed: increase backend test coverage to at least 70%.")
    }
    if ($ErrorMessage -match "cov-fail-under=65") {
        $hints.Add("Coverage gate failed: increase ACS test coverage to at least 65%.")
    }

    if ($hints.Count -eq 0) {
        $hints.Add("Review the command error in the log and re-run the failed command directly for focused debugging.")
    }

    return @($hints | Select-Object -Unique)
}

function Write-FailureSummary {
    param(
        [string]$StepName,
        [string]$ErrorMessage,
        [string]$LogPath
    )

    $why = Get-StepWhy -StepName $StepName
    $hints = Get-ResolutionHints -StepName $StepName -ErrorMessage $ErrorMessage

    Write-Host "`n=== Pre-commit failure summary ==="
    Write-Host "Failed step: $StepName"
    Write-Host "Why this is a gate: $why"
    Write-Host "Error: $ErrorMessage"
    Write-Host "How to resolve:"
    foreach ($hint in $hints) {
        Write-Host "- $hint"
    }

    if (Test-Path $LogPath) {
        Write-Host "Log file: $LogPath"
        Write-Host "Recent log output:"
        Get-Content $LogPath -Tail 25 | ForEach-Object {
            Write-Host $_
        }
    }
}

function Ensure-FrontendDependencies {
    param(
        [string]$RepoPath,
        [switch]$ForceInstall
    )

    $nodeModulesPath = Join-Path $RepoPath "node_modules"
    if ($ForceInstall -or -not (Test-Path $nodeModulesPath)) {
        Enter-Step "Install frontend dependencies"
        Invoke-Checked "npm" @("ci") $RepoPath
    }
}

function Run-FrontendFastChecks {
    param(
        [string]$RepoPath,
        [switch]$ForceInstall
    )

    Ensure-FrontendDependencies -RepoPath $RepoPath -ForceInstall:$ForceInstall

    Enter-Step "Frontend lint"
    Invoke-Checked "npm" @("run", "lint") $RepoPath

    Enter-Step "Frontend tests"
    Invoke-Checked "npm" @("run", "test") $RepoPath

    Enter-Step "Frontend build"
    Invoke-Checked "npm" @("run", "build") $RepoPath
}

function Run-BackendFastChecks {
    param(
        [string]$RepoPath,
        [string]$DatabaseUrl
    )

    $backendPath = Join-Path $RepoPath "backend"
    $backendPython = Resolve-PythonCommand -RepoPath $backendPath

    Enter-Step "Backend dependencies"
    Invoke-Checked $backendPython @("-m", "pip", "install", "--upgrade", "pip") $backendPath
    Invoke-Checked $backendPython @("-m", "pip", "install", "-e", ".") $backendPath
    Invoke-Checked $backendPython @("-m", "pip", "install", "pytest-cov") $backendPath

    Enter-Step "Backend tests with CI coverage threshold"
    $originalTestDatabaseUrl = $env:TEST_DATABASE_URL
    try {
        $env:TEST_DATABASE_URL = $DatabaseUrl
        Invoke-Checked $backendPython @("-m", "pytest", "tests", "-q", "--cov=app", "--cov-report=term-missing", "--cov-fail-under=70") $backendPath
    } finally {
        if ($null -ne $originalTestDatabaseUrl) {
            $env:TEST_DATABASE_URL = $originalTestDatabaseUrl
        } else {
            Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
        }
    }

    Enter-Step "Backend migration execution check"
    $originalDatabaseUrl = $env:DATABASE_URL
    $originalJwtSecret = $env:JWT_SECRET
    try {
        $env:DATABASE_URL = $DatabaseUrl
        $env:JWT_SECRET = "test-secret"
        Invoke-Checked $backendPython @("scripts/run_migrations.py") $backendPath
    } finally {
        if ($null -ne $originalDatabaseUrl) {
            $env:DATABASE_URL = $originalDatabaseUrl
        } else {
            Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
        }
        if ($null -ne $originalJwtSecret) {
            $env:JWT_SECRET = $originalJwtSecret
        } else {
            Remove-Item Env:JWT_SECRET -ErrorAction SilentlyContinue
        }
    }
}

function Run-AcsFastChecks {
    param(
        [string]$RepoPath,
        [string]$DatabaseUrl
    )

    $acsPath = Join-Path $RepoPath "python-acs-service"
    $acsPython = Resolve-PythonCommand -RepoPath $acsPath

    Enter-Step "ACS dependencies"
    Invoke-Checked $acsPython @("-m", "pip", "install", "--upgrade", "pip") $acsPath
    Invoke-Checked $acsPython @("-m", "pip", "install", "-r", "requirements.txt") $acsPath
    Invoke-Checked $acsPython @("-m", "pip", "install", "pytest-cov") $acsPath

    Enter-Step "ACS tests with CI coverage threshold"
    $originalTestDatabaseUrl = $env:TEST_DATABASE_URL
    try {
        $env:TEST_DATABASE_URL = $DatabaseUrl
        Invoke-Checked $acsPython @("-m", "pytest", "tests", "-q", "--cov=app", "--cov-report=term-missing", "--cov-fail-under=65") $acsPath
    } finally {
        if ($null -ne $originalTestDatabaseUrl) {
            $env:TEST_DATABASE_URL = $originalTestDatabaseUrl
        } else {
            Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
        }
    }
}

function Run-FullSecurityChecks {
    param(
        [string]$RepoPath,
        [bool]$FrontendTouched,
        [bool]$BackendTouched,
        [bool]$AcsTouched,
        [bool]$InfraTouched,
        [switch]$ForceInstall
    )

    Require-Command "docker"

    Enter-Step "Secrets scan (gitleaks)"
    Invoke-Checked "docker" @(
        "run", "--rm",
        "--mount", "type=bind,src=$RepoPath,dst=/repo",
        "zricethezav/gitleaks:v8.24.2",
        "detect", "--source", "/repo", "--verbose", "--redact", "--exit-code", "1"
    ) $RepoPath

    if ($FrontendTouched) {
        Ensure-FrontendDependencies -RepoPath $RepoPath -ForceInstall:$ForceInstall
        Enter-Step "NPM dependency audit"
        Invoke-Checked "npm" @("audit", "--audit-level=high") $RepoPath
    }

    if ($BackendTouched) {
        $backendPath = Join-Path $RepoPath "backend"
        $backendPython = Resolve-PythonCommand -RepoPath $backendPath
        Enter-Step "Backend pip-audit"
        Invoke-Checked $backendPython @("-m", "pip", "install", "--upgrade", "pip") $backendPath
        Invoke-Checked $backendPython @("-m", "pip", "install", "pip-audit") $backendPath
        Invoke-Checked $backendPython @("-m", "pip", "install", "-e", ".") $backendPath
        Invoke-Checked $backendPython @("-m", "pip_audit", "--desc", "--strict") $backendPath
    }

    if ($AcsTouched) {
        $acsPath = Join-Path $RepoPath "python-acs-service"
        $acsPython = Resolve-PythonCommand -RepoPath $acsPath
        Enter-Step "ACS pip-audit"
        Invoke-Checked $acsPython @("-m", "pip", "install", "--upgrade", "pip") $acsPath
        Invoke-Checked $acsPython @("-m", "pip", "install", "pip-audit") $acsPath
        Invoke-Checked $acsPython @("-m", "pip", "install", "-r", "requirements.txt") $acsPath
        Invoke-Checked $acsPython @("-m", "pip_audit", "--desc", "--strict", "-r", "requirements.txt") $acsPath
    }

    if ($BackendTouched -or $AcsTouched) {
        Enter-Step "Dockerfile lint (hadolint)"
        Invoke-Checked "docker" @(
            "run", "--rm",
            "--mount", "type=bind,src=$RepoPath,dst=/repo",
            "hadolint/hadolint:v2.12.0",
            "hadolint", "/repo/backend/Dockerfile"
        ) $RepoPath
        Invoke-Checked "docker" @(
            "run", "--rm",
            "--mount", "type=bind,src=$RepoPath,dst=/repo",
            "hadolint/hadolint:v2.12.0",
            "hadolint", "/repo/python-acs-service/Dockerfile"
        ) $RepoPath

        $precommitTmpPath = Join-Path $RepoPath ".tmp\precommit"
        New-Item -ItemType Directory -Path $precommitTmpPath -Force | Out-Null

        $shortSha = (git -C $RepoPath rev-parse --short HEAD).Trim()
        if (-not $shortSha) {
            $shortSha = "local"
        }

        $backendTag = "local/backend-precommit-scan:$shortSha"
        $acsTag = "local/acs-precommit-scan:$shortSha"

        Enter-Step "Build local images for vulnerability scan"
        Invoke-Checked "docker" @("build", "-t", $backendTag, "backend") $RepoPath
        Invoke-Checked "docker" @("build", "-t", $acsTag, "python-acs-service") $RepoPath

        $backendTar = Join-Path $precommitTmpPath "backend-image.tar"
        $acsTar = Join-Path $precommitTmpPath "acs-image.tar"
        Invoke-Checked "docker" @("save", $backendTag, "-o", $backendTar) $RepoPath
        Invoke-Checked "docker" @("save", $acsTag, "-o", $acsTar) $RepoPath

        Enter-Step "Image vulnerability scan (trivy)"
        Invoke-Checked "docker" @(
            "run", "--rm",
            "--mount", "type=bind,src=$precommitTmpPath,dst=/scan",
            "aquasec/trivy:0.56.2",
            "image", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--ignore-unfixed",
            "--input", "/scan/backend-image.tar"
        ) $RepoPath
        Invoke-Checked "docker" @(
            "run", "--rm",
            "--mount", "type=bind,src=$precommitTmpPath,dst=/scan",
            "aquasec/trivy:0.56.2",
            "image", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--ignore-unfixed",
            "--input", "/scan/acs-image.tar"
        ) $RepoPath
    }

    if ($InfraTouched) {
        Require-Command "az"
        $backendPath = Join-Path $RepoPath "backend"
        $backendPython = Resolve-PythonCommand -RepoPath $backendPath

        Enter-Step "Bicep compile validation"
        Invoke-Checked "az" @("bicep", "install") $RepoPath
        Invoke-Checked "az" @("bicep", "build", "--file", "infra/dev/main.bicep") $RepoPath
        Invoke-Checked "az" @("bicep", "build", "--file", "infra/uat/main.bicep") $RepoPath
        Invoke-Checked "az" @("bicep", "build", "--file", "infra/prod/main.bicep") $RepoPath

        Enter-Step "IaC policy scan (checkov)"
        Invoke-Checked $backendPython @("-m", "pip", "install", "checkov") $backendPath
        Invoke-Checked $backendPython @("-m", "checkov", "-d", "infra", "--quiet", "--compact", "--framework", "bicep") $RepoPath
    }

    Enter-Step "CodeQL note"
    Write-Host "CodeQL analysis remains CI-only and is not run in local pre-commit."
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
if (-not (Test-Path (Join-Path $repoRootResolved ".git"))) {
    throw "Repo root must contain a .git directory. Received: $repoRootResolved"
}

$precommitLogDir = Join-Path $repoRootResolved ".tmp\precommit"
New-Item -ItemType Directory -Path $precommitLogDir -Force | Out-Null
$timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$script:PreCommitLogPath = Join-Path $precommitLogDir "precommit-$timestamp.log"

$transcriptStarted = $false
try {
    Start-Transcript -Path $script:PreCommitLogPath -Force | Out-Null
    $transcriptStarted = $true
} catch {
    Write-Host "Warning: could not start transcript logging: $_"
}

$exitCode = 0
$startedLocalPostgres = $false
$failureDetails = $null

try {
    Write-Host "Pre-commit log file: $script:PreCommitLogPath"

    Enter-Step "Detect changed files"
    $changedFiles = Get-ChangedFiles -RepoPath $repoRootResolved -Selection $Scope
    $skipChecks = $false
    if ($Scope -eq "staged" -and $changedFiles.Count -eq 0) {
        Write-Host "No staged files detected. Skipping pre-commit checks."
        $skipChecks = $true
    }

    if (-not $skipChecks) {
        $workflowTouched = Has-PathMatch -Files $changedFiles -Prefixes @(".github/workflows/")
        $runAllChecks = ($Scope -eq "all") -or $workflowTouched

        $frontendTouched = $runAllChecks -or (Has-PathMatch -Files $changedFiles -Prefixes @("src/", "public/") -Exact @(
            "package.json",
            "package-lock.json",
            "eslint.config.js",
            "vite.config.js",
            "tailwind.config.js",
            "postcss.config.js",
            "index.html"
        ))

        $backendTouched = $runAllChecks -or (Has-PathMatch -Files $changedFiles -Prefixes @("backend/") -Exact @("backend/pyproject.toml"))
        $acsTouched = $runAllChecks -or (Has-PathMatch -Files $changedFiles -Prefixes @("python-acs-service/"))
        $infraTouched = $runAllChecks -or (Has-PathMatch -Files $changedFiles -Prefixes @("infra/") -Exact @(".github/workflows/infra-dev.yml"))

        Enter-Step "Pre-commit scope"
        Write-Host "Scope: $Scope"
        Write-Host "Profile: $Profile"
        Write-Host "Files detected: $($changedFiles.Count)"
        Write-Host "Frontend checks: $frontendTouched"
        Write-Host "Backend checks: $backendTouched"
        Write-Host "ACS checks: $acsTouched"
        Write-Host "Infra checks: $infraTouched"

        try {
            if (($backendTouched -or $acsTouched) -and -not $SkipDatabaseBootstrap) {
                $additionalDatabases = @()
                if ($backendTouched) {
                    $additionalDatabases += (Get-DatabaseNameFromUrl $BackendDatabaseUrl)
                }
                if ($acsTouched) {
                    $additionalDatabases += (Get-DatabaseNameFromUrl $AcsDatabaseUrl)
                }
                $additionalDatabases = @($additionalDatabases | Select-Object -Unique)

                Enter-Step "Start local PostgreSQL test dependencies"
                & (Join-Path $PSScriptRoot "start-local-postgres.ps1") `
                    -RepoRoot $repoRootResolved `
                    -PostgresUser "postgres" `
                    -PostgresPassword "postgres" `
                    -PostgresDb "postgres" `
                    -AdditionalDatabases $additionalDatabases
                $startedLocalPostgres = $true
            }

            if ($frontendTouched) {
                Run-FrontendFastChecks -RepoPath $repoRootResolved -ForceInstall:$InstallDependencies
            }
            if ($backendTouched) {
                Run-BackendFastChecks -RepoPath $repoRootResolved -DatabaseUrl $BackendDatabaseUrl
            }
            if ($acsTouched) {
                Run-AcsFastChecks -RepoPath $repoRootResolved -DatabaseUrl $AcsDatabaseUrl
            }

            if ($Profile -eq "full") {
                Run-FullSecurityChecks `
                    -RepoPath $repoRootResolved `
                    -FrontendTouched:$frontendTouched `
                    -BackendTouched:$backendTouched `
                    -AcsTouched:$acsTouched `
                    -InfraTouched:$infraTouched `
                    -ForceInstall:$InstallDependencies
            }
        } finally {
            if ($startedLocalPostgres) {
                try {
                    Enter-Step "Stop local PostgreSQL"
                    Invoke-Checked "docker" @("compose", "stop", "postgres") $repoRootResolved
                } catch {
                    Write-Host "Failed to stop local PostgreSQL: $_"
                }
            }
        }

        $script:CurrentStepName = ""
        Write-Host "`nPre-commit checks completed successfully."
        Write-Host "Log file: $script:PreCommitLogPath"
    }
} catch {
    $exitCode = 1
    $failedStep = if ($script:CurrentStepName) { $script:CurrentStepName } else { "Unknown step" }
    $errorMessage = $_.Exception.Message
    $failureDetails = [pscustomobject]@{
        StepName = $failedStep
        ErrorMessage = $errorMessage
    }
} finally {
    if ($transcriptStarted) {
        try {
            Stop-Transcript | Out-Null
        } catch {
            Write-Host "Warning: could not stop transcript cleanly: $_"
        }
    }
}

if ($exitCode -ne 0 -and $null -ne $failureDetails) {
    Write-FailureSummary -StepName $failureDetails.StepName -ErrorMessage $failureDetails.ErrorMessage -LogPath $script:PreCommitLogPath
}

exit $exitCode
