param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$TenantId = "",
    [string]$Repo = "dcava30/Talenti_MVP",
    [string]$Branch = "main",
    [string]$GitHubEnvironment = "dev",

    [string]$Location = "australiaeast",
    [string]$ResourceGroup = "rg-talenti-dev-aue",

    [string]$AcrName = "acrtalentidev",
    [string]$KeyVaultName = "kv-talenti-dev-aue",
    [string]$StorageAccountName = "sttalentidevaue",

    [string]$BackendApp = "ca-backend-dev",
    [string]$BackendWorkerApp = "ca-backend-worker-dev",
    [string]$Model1App = "ca-model1-dev",
    [string]$Model2App = "ca-model2-dev",
    [string]$AcsWorkerApp = "ca-acs-worker-dev",

    [string]$PostgresServer = "psql-talenti-dev-aue",
    [string]$PostgresDb = "talenti_backend_dev",
    [string]$PostgresAdminUser = "talentiadmin",
    [SecureString]$PostgresAdminPassword,

    [string]$AcsResource = "acs-talenti-dev-aue",
    [string]$SpeechResource = "speech-talenti-dev-aue",
    [string]$OpenAIResource = "oai-talenti-dev-aue",
    [string]$OpenAIRegion = "australiaeast",
    [string]$OpenAIDeployment = "gpt-4o",

    [string]$StaticWebApp = "swa-talenti-dev-aue",

    [string]$FrontendOrigin = "",
    [string]$JwtSecret = "",
    [string]$AcsWorkerSharedSecret = "",
    [string]$AlertEmailAddress = "",
    [string]$Model1ImageRef = "",
    [string]$Model2ImageRef = "",

    [switch]$RunWorkflows
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

function New-RandomSecret {
    param([int]$Length = 48)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    -join (1..$Length | ForEach-Object { $chars[(Get-Random -Minimum 0 -Maximum $chars.Length)] })
}

function Convert-SecureToPlain {
    param([SecureString]$Value)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Ensure-AzRoleAssignment {
    param(
        [string]$PrincipalId,
        [string]$Role,
        [string]$Scope
    )

    az role assignment create `
        --assignee-object-id $PrincipalId `
        --assignee-principal-type ServicePrincipal `
        --role $Role `
        --scope $Scope 2>$null | Out-Null
}

function Ensure-Container {
    param(
        [string]$Account,
        [string]$Key,
        [string]$Name
    )

    az storage container create --name $Name --account-name $Account --account-key $Key --auth-mode key | Out-Null
}

if ($GitHubEnvironment -ne "dev") {
    throw "day1-dev-deploy.ps1 configures the dev environment only. Use -GitHubEnvironment dev."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$infraTemplate = Join-Path $repoRoot "infra/dev/main.bicep"
$parametersPath = Join-Path $repoRoot "infra/dev/parameters.dev.json"
$setupAccessScript = Join-Path $PSScriptRoot "setup-deployment-access.ps1"

if (-not (Test-Path $infraTemplate)) {
    throw "Missing infra template: $infraTemplate"
}

if (-not (Test-Path $parametersPath)) {
    throw "Missing infra parameters: $parametersPath"
}

if (-not (Test-Path $setupAccessScript)) {
    throw "Missing helper script: $setupAccessScript"
}

Require-Command "az"
Require-Command "gh"

if (-not $JwtSecret) {
    $JwtSecret = New-RandomSecret -Length 64
}
if (-not $AcsWorkerSharedSecret) {
    $AcsWorkerSharedSecret = New-RandomSecret -Length 48
}
if (-not $PostgresAdminPassword) {
    $PostgresAdminPassword = Read-Host "Postgres admin password" -AsSecureString
}
$PostgresPasswordPlain = Convert-SecureToPlain -Value $PostgresAdminPassword

if (-not $AlertEmailAddress) {
    throw "AlertEmailAddress is required because infra/dev/main.bicep provisions Azure Monitor alerting resources."
}

Write-Section "Login and prerequisites"
az extension add --name containerapp --upgrade | Out-Null
az extension add --name staticwebapp --upgrade | Out-Null
az account set --subscription $SubscriptionId
if (-not $TenantId) {
    $TenantId = az account show --subscription $SubscriptionId --query tenantId -o tsv
}
if (-not $TenantId) {
    throw "Unable to resolve tenant id from Azure CLI. Pass -TenantId explicitly after running az login."
}
az group create --name $ResourceGroup --location $Location | Out-Null

$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run 'gh auth login' and rerun."
}

Write-Section "Deploy infra (Bicep)"
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file $infraTemplate `
    --parameters "@$parametersPath" `
    --parameters "postgresAdminUser=$PostgresAdminUser" "postgresAdminPassword=$PostgresPasswordPlain" "alertEmailAddress=$AlertEmailAddress" | Out-Null

Write-Section "Create ACS/Speech/OpenAI resources if missing"
$null = az communication show --name $AcsResource --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    az communication create --name $AcsResource --resource-group $ResourceGroup --data-location "Australia" | Out-Null
}

$null = az cognitiveservices account show --name $SpeechResource --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    az cognitiveservices account create `
        --name $SpeechResource `
        --resource-group $ResourceGroup `
        --kind SpeechServices `
        --sku S0 `
        --location $Location `
        --yes | Out-Null
}

$null = az cognitiveservices account show --name $OpenAIResource --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    az cognitiveservices account create `
        --name $OpenAIResource `
        --resource-group $ResourceGroup `
        --kind OpenAI `
        --sku S0 `
        --location $OpenAIRegion `
        --yes | Out-Null
}

$null = az cognitiveservices account deployment show --name $OpenAIResource --resource-group $ResourceGroup --deployment-name $OpenAIDeployment 2>$null
if ($LASTEXITCODE -ne 0) {
    az cognitiveservices account deployment create `
        --name $OpenAIResource `
        --resource-group $ResourceGroup `
        --deployment-name $OpenAIDeployment `
        --model-name "gpt-4o" `
        --model-format OpenAI `
        --model-version "latest" `
        --sku-name Standard `
        --sku-capacity 10 | Out-Null
}

Write-Section "Gather keys and endpoints"
$acsConnection = az communication list-key --name $AcsResource --resource-group $ResourceGroup --query primaryConnectionString -o tsv
$speechKey = az cognitiveservices account keys list --name $SpeechResource --resource-group $ResourceGroup --query key1 -o tsv
$speechRegion = $Location

$openAIEndpoint = az cognitiveservices account show --name $OpenAIResource --resource-group $ResourceGroup --query properties.endpoint -o tsv
$openAIKey = az cognitiveservices account keys list --name $OpenAIResource --resource-group $ResourceGroup --query key1 -o tsv

$storageKey = az storage account keys list --resource-group $ResourceGroup --account-name $StorageAccountName --query "[0].value" -o tsv
$storageConnection = az storage account show-connection-string --resource-group $ResourceGroup --name $StorageAccountName --query connectionString -o tsv

$pgHost = az postgres flexible-server show --resource-group $ResourceGroup --name $PostgresServer --query fullyQualifiedDomainName -o tsv
$databaseUrl = "postgresql+psycopg://${PostgresAdminUser}:${PostgresPasswordPlain}@$pgHost:5432/$PostgresDb?sslmode=require"

Write-Section "Ensure storage containers"
Ensure-Container -Account $StorageAccountName -Key $storageKey -Name "uploads"
Ensure-Container -Account $StorageAccountName -Key $storageKey -Name "recordings"

Write-Section "Store secrets in Key Vault"
az keyvault secret set --vault-name $KeyVaultName --name "backend-database-url" --value $databaseUrl | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "jwt-secret" --value $JwtSecret | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "acs-worker-shared-secret" --value $AcsWorkerSharedSecret | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-acs-connection-string" --value $acsConnection | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-speech-key" --value $speechKey | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-openai-endpoint" --value $openAIEndpoint | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-openai-api-key" --value $openAIKey | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-storage-account" --value $StorageAccountName | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-storage-account-key" --value $storageKey | Out-Null
az keyvault secret set --vault-name $KeyVaultName --name "azure-storage-connection" --value $storageConnection | Out-Null

Write-Section "Assign AcrPull and Key Vault roles to container apps"
$acrId = az acr show --name $AcrName --resource-group $ResourceGroup --query id -o tsv
$kvId = az keyvault show --name $KeyVaultName --resource-group $ResourceGroup --query id -o tsv
foreach ($app in @($BackendApp, $BackendWorkerApp, $Model1App, $Model2App, $AcsWorkerApp)) {
    $principal = az containerapp show --name $app --resource-group $ResourceGroup --query identity.principalId -o tsv
    if ($principal) {
        Ensure-AzRoleAssignment -PrincipalId $principal -Role "AcrPull" -Scope $acrId
        Ensure-AzRoleAssignment -PrincipalId $principal -Role "Key Vault Secrets User" -Scope $kvId
    }
}

Write-Section "Configure ingress modes"
az containerapp ingress enable --name $BackendApp --resource-group $ResourceGroup --type external --target-port 8000 | Out-Null
az containerapp ingress enable --name $Model1App --resource-group $ResourceGroup --type internal --target-port 8001 | Out-Null
az containerapp ingress enable --name $Model2App --resource-group $ResourceGroup --type internal --target-port 8002 | Out-Null
az containerapp ingress enable --name $AcsWorkerApp --resource-group $ResourceGroup --type internal --target-port 8000 | Out-Null

Write-Section "Resolve service URLs"
$backendFqdn = az containerapp show --name $BackendApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
$model1Fqdn = az containerapp show --name $Model1App --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
$model2Fqdn = az containerapp show --name $Model2App --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
$workerFqdn = az containerapp show --name $AcsWorkerApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv

$publicBaseUrl = "https://$backendFqdn"
$model1Url = "https://$model1Fqdn"
$model2Url = "https://$model2Fqdn"
$workerUrl = "https://$workerFqdn"

if (-not $FrontendOrigin) {
    $FrontendOrigin = "https://$StaticWebApp.azurestaticapps.net"
}
$allowedOriginsJson = "[`"$FrontendOrigin`"]"

Write-Section "Set Container App secrets"
az containerapp secret set --name $BackendApp --resource-group $ResourceGroup --secrets `
    database-url="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/backend-database-url,identityref:system" `
    jwt-secret="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/jwt-secret,identityref:system" `
    acs-worker-shared-secret="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/acs-worker-shared-secret,identityref:system" `
    azure-acs-connection-string="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-acs-connection-string,identityref:system" `
    azure-speech-key="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-speech-key,identityref:system" `
    azure-openai-endpoint="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-openai-endpoint,identityref:system" `
    azure-openai-api-key="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-openai-api-key,identityref:system" `
    azure-storage-account="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-storage-account,identityref:system" `
    azure-storage-account-key="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-storage-account-key,identityref:system" | Out-Null

az containerapp secret set --name $BackendWorkerApp --resource-group $ResourceGroup --secrets `
    database-url="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/backend-database-url,identityref:system" `
    jwt-secret="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/jwt-secret,identityref:system" `
    acs-worker-shared-secret="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/acs-worker-shared-secret,identityref:system" `
    azure-storage-account="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-storage-account,identityref:system" `
    azure-storage-account-key="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-storage-account-key,identityref:system" | Out-Null

az containerapp secret set --name $AcsWorkerApp --resource-group $ResourceGroup --secrets `
    acs-connection-string="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-acs-connection-string,identityref:system" `
    az-storage-connection="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/azure-storage-connection,identityref:system" `
    acs-worker-shared-secret="keyvaultref:https://$KeyVaultName.vault.azure.net/secrets/acs-worker-shared-secret,identityref:system" | Out-Null

Write-Section "Set Container App environment variables"
az containerapp update --name $BackendApp --resource-group $ResourceGroup --set-env-vars `
    DATABASE_URL=secretref:database-url `
    JWT_SECRET=secretref:jwt-secret `
    ENVIRONMENT=development `
    ALLOWED_ORIGINS=$allowedOriginsJson `
    MODEL_SERVICE_1_URL=$model1Url `
    MODEL_SERVICE_2_URL=$model2Url `
    ACS_WORKER_URL=$workerUrl `
    ACS_WORKER_SHARED_SECRET=secretref:acs-worker-shared-secret `
    PUBLIC_BASE_URL=$publicBaseUrl `
    AZURE_ACS_CONNECTION_STRING=secretref:azure-acs-connection-string `
    AZURE_SPEECH_KEY=secretref:azure-speech-key `
    AZURE_SPEECH_REGION=$speechRegion `
    AZURE_OPENAI_ENDPOINT=secretref:azure-openai-endpoint `
    AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key `
    AZURE_OPENAI_DEPLOYMENT=$OpenAIDeployment `
    AZURE_STORAGE_ACCOUNT=secretref:azure-storage-account `
    AZURE_STORAGE_ACCOUNT_KEY=secretref:azure-storage-account-key `
    AZURE_STORAGE_CONTAINER=uploads | Out-Null

az containerapp update --name $BackendWorkerApp --resource-group $ResourceGroup --set-env-vars `
    DATABASE_URL=secretref:database-url `
    JWT_SECRET=secretref:jwt-secret `
    ENVIRONMENT=development `
    MODEL_SERVICE_1_URL=$model1Url `
    MODEL_SERVICE_2_URL=$model2Url `
    ACS_WORKER_URL=$workerUrl `
    ACS_WORKER_SHARED_SECRET=secretref:acs-worker-shared-secret `
    PUBLIC_BASE_URL=$publicBaseUrl `
    AZURE_STORAGE_ACCOUNT=secretref:azure-storage-account `
    AZURE_STORAGE_ACCOUNT_KEY=secretref:azure-storage-account-key `
    AZURE_STORAGE_CONTAINER=uploads `
    BACKGROUND_WORKER_POLL_INTERVAL_SECONDS=2.0 `
    AUTO_SCORE_INTERVIEWS=false | Out-Null

az containerapp update --name $AcsWorkerApp --resource-group $ResourceGroup --set-env-vars `
    ACS_CONNECTION_STRING=secretref:acs-connection-string `
    AZURE_STORAGE_CONNECTION_STRING=secretref:az-storage-connection `
    RECORDING_CONTAINER=recordings `
    BACKEND_INTERNAL_URL=$publicBaseUrl `
    ACS_WORKER_SHARED_SECRET=secretref:acs-worker-shared-secret `
    ACS_CALLBACK_URL="$publicBaseUrl/api/v1/acs/webhook" `
    ENVIRONMENT=development | Out-Null

Write-Section "Create Static Web App if missing"
$null = az staticwebapp show --name $StaticWebApp --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    az staticwebapp create --name $StaticWebApp --resource-group $ResourceGroup --location $Location --sku Standard | Out-Null
}

Write-Section "Configure GitHub deployment environment"
& $setupAccessScript `
    -SubscriptionId $SubscriptionId `
    -TenantId $TenantId `
    -Repo $Repo `
    -EnvironmentNames @($GitHubEnvironment) `
    -Location $Location `
    -AlertEmailAddress $AlertEmailAddress `
    -PostgresAdminPassword $PostgresPasswordPlain `
    -BackendDatabaseUrl $databaseUrl `
    -JwtSecret $JwtSecret `
    -Model1ImageRef $Model1ImageRef `
    -Model2ImageRef $Model2ImageRef

if ($RunWorkflows) {
    Write-Section "Trigger GitHub workflows"
    gh workflow run infra-dev.yml --ref $Branch
    gh workflow run deploy-dev.yml --ref $Branch
}

Write-Section "Done"
Write-Host "Backend URL: $publicBaseUrl"
Write-Host "Backend worker app: $BackendWorkerApp"
Write-Host "Model1 URL (internal): $model1Url"
Write-Host "Model2 URL (internal): $model2Url"
Write-Host "ACS Worker URL (internal): $workerUrl"
Write-Host "Frontend origin configured: $FrontendOrigin"
Write-Host ""
Write-Host "Next:"
Write-Host "1) Set MODEL1_IMAGE_REF and MODEL2_IMAGE_REF in GitHub environment 'dev' if you did not pass them today."
Write-Host "2) Ensure ALERT_EMAIL_ADDRESS is set in GitHub environment 'dev' if you did not pass it today."
Write-Host "3) Run deploy-dev workflow if not triggered."
Write-Host "4) Verify $publicBaseUrl/health returns 200."
