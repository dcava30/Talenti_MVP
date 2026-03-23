param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EnvFile = ".env.azure",
    [string]$ResourceGroup = "rg-talenti-dev-aue",
    [string]$KeyVaultName = "kv-talenti-dev-aue",
    [string]$SpeechResource = "speech-talenti-dev-aue",
    [string]$OpenAIResource = "oai-talenti-dev-aue",
    [string]$OpenAIDeployment = "gpt-4o",
    [string]$StaticWebApp = "swa-talenti-dev-aue",
    [string]$BackendApp = "ca-backend-dev",
    [string]$FrontendOrigin = "",
    [string]$ApiBaseUrl = "",
    [int]$Model1Port = 8001,
    [int]$Model2Port = 8002,
    [int]$AcsWorkerPort = 8010,
    [switch]$EnableLiveScoring,
    [switch]$EnableAcsCallAutomation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Import-EnvFile {
    param([string]$Path)

    foreach ($line in Get-Content -Path $Path) {
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $delimiterIndex = $line.IndexOf("=")
        if ($delimiterIndex -lt 1) {
            continue
        }

        $name = $line.Substring(0, $delimiterIndex)
        $value = $line.Substring($delimiterIndex + 1)
        Set-Item -Path "Env:$name" -Value $value
    }
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$envFilePath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $repoRootResolved $EnvFile
}

$exportScript = Join-Path $PSScriptRoot "export-azure-env.ps1"
if (-not (Test-Path $exportScript)) {
    throw "Missing helper script: $exportScript"
}

Write-Section "Export Azure-backed environment"
& $exportScript `
    -SubscriptionId $SubscriptionId `
    -ResourceGroup $ResourceGroup `
    -KeyVaultName $KeyVaultName `
    -SpeechResource $SpeechResource `
    -OpenAIResource $OpenAIResource `
    -OpenAIDeployment $OpenAIDeployment `
    -StaticWebApp $StaticWebApp `
    -BackendApp $BackendApp `
    -Profile deployed `
    -OutputPath $envFilePath `
    -FrontendOrigin $FrontendOrigin `
    -ApiBaseUrl $ApiBaseUrl

Import-EnvFile -Path $envFilePath

if ($EnableLiveScoring) {
    $env:MODEL_SERVICE_1_URL = "http://localhost:$Model1Port"
    $env:MODEL_SERVICE_2_URL = "http://localhost:$Model2Port"
    $env:ENABLE_LIVE_SCORING = "true"
} else {
    $env:MODEL_SERVICE_1_URL = ""
    $env:MODEL_SERVICE_2_URL = ""
    $env:ENABLE_LIVE_SCORING = "false"
}

if ($EnableAcsCallAutomation) {
    $env:ACS_WORKER_URL = "http://localhost:$AcsWorkerPort"
    $env:ENABLE_ACS_CALL_AUTOMATION = "true"
} else {
    $env:ACS_WORKER_URL = ""
    $env:ENABLE_ACS_CALL_AUTOMATION = "false"
}

$backendPath = Join-Path $repoRootResolved "backend"
$backendPython = Join-Path $backendPath ".venv\\Scripts\\python.exe"
if (-not (Test-Path $backendPython)) {
    throw "Backend runtime not found at $backendPython. Run .\\scripts\\bootstrap-local-deps.ps1 first."
}

Write-Section "Start backend-worker"
Push-Location $backendPath
try {
    & $backendPython -m app.worker_main
} finally {
    Pop-Location
}
