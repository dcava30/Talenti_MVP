param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$ResourceGroup = "rg-talenti-dev-aue",
    [string]$KeyVaultName = "kv-talenti-dev-aue",
    [string]$SpeechResource = "speech-talenti-dev-aue",
    [string]$OpenAIResource = "oai-talenti-dev-aue",
    [string]$OpenAIDeployment = "gpt-4o",
    [string]$StaticWebApp = "swa-talenti-dev-aue",
    [string]$BackendApp = "ca-backend-dev",
    [string]$Model1App = "ca-model1-dev",
    [string]$Model2App = "ca-model2-dev",
    [string]$AcsWorkerApp = "ca-acs-worker-dev",

    [ValidateSet("local", "deployed")]
    [string]$Profile = "local",

    [string]$OutputPath = ".env.azure",
    [string]$FrontendOrigin = "",
    [int]$FrontendPort = 5173,
    [int]$BackendPort = 8000,
    [int]$Model1Port = 8001,
    [int]$Model2Port = 8002,
    [int]$AcsWorkerPort = 8010
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-AzValue {
    param(
        [string[]]$Args,
        [switch]$AllowEmpty
    )

    $output = & az @Args 2>$null
    if ($LASTEXITCODE -ne 0) {
        if ($AllowEmpty) {
            return ""
        }
        throw "Azure CLI command failed: az $($Args -join ' ')"
    }

    if ($null -eq $output) {
        return ""
    }

    return ($output | Out-String).Trim()
}

function Get-KeyVaultSecret {
    param([string]$SecretName)

    return Get-AzValue -Args @(
        "keyvault", "secret", "show",
        "--vault-name", $KeyVaultName,
        "--name", $SecretName,
        "--query", "value",
        "-o", "tsv"
    ) -AllowEmpty
}

function Resolve-ContainerAppUrl {
    param(
        [string]$AppName,
        [string]$Fallback
    )

    $fqdn = Get-AzValue -Args @(
        "containerapp", "show",
        "--name", $AppName,
        "--resource-group", $ResourceGroup,
        "--query", "properties.configuration.ingress.fqdn",
        "-o", "tsv"
    ) -AllowEmpty

    if ($fqdn) {
        return "https://$fqdn"
    }

    return $Fallback
}

function Resolve-FrontendOrigin {
    if ($FrontendOrigin) {
        return $FrontendOrigin
    }

    if ($Profile -eq "deployed") {
        $defaultHostname = Get-AzValue -Args @(
            "staticwebapp", "show",
            "--name", $StaticWebApp,
            "--resource-group", $ResourceGroup,
            "--query", "defaultHostname",
            "-o", "tsv"
        ) -AllowEmpty

        if ($defaultHostname) {
            return "https://$defaultHostname"
        }
    }

    return "http://localhost:$FrontendPort"
}

Write-Section "Prerequisites"
Require-Command "az"
az account set --subscription $SubscriptionId

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $repoRoot $OutputPath
}

Write-Section "Read Azure secrets and endpoints"
$databaseUrl = Get-KeyVaultSecret -SecretName "backend-database-url"
$jwtSecret = Get-KeyVaultSecret -SecretName "jwt-secret"
$acsWorkerSharedSecret = Get-KeyVaultSecret -SecretName "acs-worker-shared-secret"
$acsConnection = Get-KeyVaultSecret -SecretName "azure-acs-connection-string"
$speechKey = Get-KeyVaultSecret -SecretName "azure-speech-key"
$openAIEndpoint = Get-KeyVaultSecret -SecretName "azure-openai-endpoint"
$openAIKey = Get-KeyVaultSecret -SecretName "azure-openai-api-key"
$storageAccount = Get-KeyVaultSecret -SecretName "azure-storage-account"
$storageAccountKey = Get-KeyVaultSecret -SecretName "azure-storage-account-key"
$storageConnection = Get-KeyVaultSecret -SecretName "azure-storage-connection"

$speechRegion = Get-AzValue -Args @(
    "cognitiveservices", "account", "show",
    "--name", $SpeechResource,
    "--resource-group", $ResourceGroup,
    "--query", "location",
    "-o", "tsv"
) -AllowEmpty

if (-not $speechRegion) {
    $speechRegion = Get-AzValue -Args @(
        "cognitiveservices", "account", "show",
        "--name", $OpenAIResource,
        "--resource-group", $ResourceGroup,
        "--query", "location",
        "-o", "tsv"
    ) -AllowEmpty
}

$frontendOriginResolved = Resolve-FrontendOrigin

if ($Profile -eq "deployed") {
    $publicBaseUrl = Resolve-ContainerAppUrl -AppName $BackendApp -Fallback "http://localhost:$BackendPort"
    $model1Url = Resolve-ContainerAppUrl -AppName $Model1App -Fallback "http://localhost:$Model1Port"
    $model2Url = Resolve-ContainerAppUrl -AppName $Model2App -Fallback "http://localhost:$Model2Port"
    $acsWorkerUrl = Resolve-ContainerAppUrl -AppName $AcsWorkerApp -Fallback "http://localhost:$AcsWorkerPort"
    $viteApiBaseUrl = $publicBaseUrl
} else {
    $publicBaseUrl = "http://localhost:$BackendPort"
    $model1Url = "http://localhost:$Model1Port"
    $model2Url = "http://localhost:$Model2Port"
    $acsWorkerUrl = "http://localhost:$AcsWorkerPort"
    $viteApiBaseUrl = "http://localhost:$BackendPort"
}

$allowedOriginsJson = "[`"$frontendOriginResolved`"]"
$callbackUrl = "$publicBaseUrl/api/v1/acs/webhook"

Write-Section "Write env file"
$envLines = @(
    "VITE_API_BASE_URL=$viteApiBaseUrl"
    ""
    "# Backend"
    "DATABASE_URL=$databaseUrl"
    "BACKEND_DATABASE_URL=$databaseUrl"
    "JWT_SECRET=$jwtSecret"
    "ENVIRONMENT=development"
    "ALLOWED_ORIGINS=$allowedOriginsJson"
    "MODEL_SERVICE_1_URL=$model1Url"
    "MODEL_SERVICE_2_URL=$model2Url"
    "ACS_WORKER_URL=$acsWorkerUrl"
    "ACS_WORKER_SHARED_SECRET=$acsWorkerSharedSecret"
    "PUBLIC_BASE_URL=$publicBaseUrl"
    ""
    "# Azure Communication Services"
    "AZURE_ACS_CONNECTION_STRING=$acsConnection"
    ""
    "# Azure Speech Services"
    "AZURE_SPEECH_KEY=$speechKey"
    "AZURE_SPEECH_REGION=$speechRegion"
    ""
    "# Azure OpenAI"
    "AZURE_OPENAI_ENDPOINT=$openAIEndpoint"
    "AZURE_OPENAI_API_KEY=$openAIKey"
    "AZURE_OPENAI_DEPLOYMENT=$OpenAIDeployment"
    ""
    "# Azure Blob Storage"
    "AZURE_STORAGE_ACCOUNT=$storageAccount"
    "AZURE_STORAGE_ACCOUNT_KEY=$storageAccountKey"
    "AZURE_STORAGE_CONTAINER=uploads"
    "AZURE_STORAGE_CONNECTION_STRING=$storageConnection"
    ""
    "# ACS worker"
    "ACS_CONNECTION_STRING=$acsConnection"
    "RECORDING_CONTAINER=recordings"
    "BACKEND_INTERNAL_URL=$publicBaseUrl"
    "ACS_CALLBACK_URL=$callbackUrl"
)

Set-Content -Path $resolvedOutputPath -Value $envLines -Encoding ASCII

Write-Section "Done"
Write-Host "Profile: $Profile"
Write-Host "Output:  $resolvedOutputPath"
Write-Host "Frontend origin: $frontendOriginResolved"
Write-Host "Public base URL: $publicBaseUrl"
