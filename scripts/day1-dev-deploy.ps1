param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [string]$TenantId,

    [string]$Repo = "dcava30/Talenti_MVP",
    [string]$Branch = "develop",

    [string]$Location = "australiaeast",
    [string]$ResourceGroup = "rg-talenti-dev-aue",

    [string]$AcrName = "acrtalentidev",
    [string]$KeyVaultName = "kv-talenti-dev-aue",
    [string]$StorageAccountName = "sttalentidevaue",

    [string]$BackendApp = "ca-backend-dev",
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
    [string]$OidcAppName = "gh-talenti-dev-oidc",

    [string]$FrontendOrigin = "",
    [string]$JwtSecret = "",
    [string]$AcsWorkerSharedSecret = "",

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

function Ensure-GhSecret {
    param(
        [string]$Name,
        [string]$Value
    )
    gh secret set $Name --body $Value | Out-Null
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

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$infraTemplate = Join-Path $repoRoot "infra/dev/main.bicep"
$parametersPath = Join-Path $repoRoot "infra/dev/parameters.dev.json"

if (-not (Test-Path $infraTemplate)) {
    throw "Missing infra template: $infraTemplate"
}

if (-not (Test-Path $parametersPath)) {
    throw "Missing infra parameters: $parametersPath"
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

Write-Section "Login and prerequisites"
az extension add --name containerapp --upgrade | Out-Null
az account set --subscription $SubscriptionId
az group create --name $ResourceGroup --location $Location | Out-Null

$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run 'gh auth login' and rerun."
}

Write-Section "Create or reuse OIDC app"
$oidcAppId = az ad app list --display-name $OidcAppName --query "[0].appId" -o tsv
if (-not $oidcAppId) {
    $oidcAppId = az ad app create --display-name $OidcAppName --query appId -o tsv
}

$spObjId = az ad sp list --filter "appId eq '$oidcAppId'" --query "[0].id" -o tsv
if (-not $spObjId) {
    $spObjId = az ad sp create --id $oidcAppId --query id -o tsv
}

$rgId = az group show --name $ResourceGroup --query id -o tsv
Ensure-AzRoleAssignment -PrincipalId $spObjId -Role "Contributor" -Scope $rgId

$federatedName = "github-$Branch"
$existingFederated = az ad app federated-credential list --id $oidcAppId --query "[?name=='$federatedName'].name | [0]" -o tsv
if (-not $existingFederated) {
    $tmpFed = Join-Path $env:TEMP "talenti-fed-$([guid]::NewGuid().ToString('N')).json"
    @"
{
  "name": "$federatedName",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:$Repo:ref:refs/heads/$Branch",
  "audiences": [ "api://AzureADTokenExchange" ]
}
"@ | Set-Content -Path $tmpFed -Encoding UTF8
    az ad app federated-credential create --id $oidcAppId --parameters $tmpFed | Out-Null
    Remove-Item $tmpFed -Force
}

Write-Section "Set GitHub OIDC secrets"
Ensure-GhSecret -Name "AZURE_CLIENT_ID" -Value $oidcAppId
Ensure-GhSecret -Name "AZURE_TENANT_ID" -Value $TenantId
Ensure-GhSecret -Name "AZURE_SUBSCRIPTION_ID" -Value $SubscriptionId

Write-Section "Deploy infra (Bicep)"
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file $infraTemplate `
    --parameters "@$parametersPath" `
    --parameters "postgresAdminUser=$PostgresAdminUser" "postgresAdminPassword=$PostgresPasswordPlain" | Out-Null

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

Write-Section "Gather keys/endpoints"
$acsConnection = az communication list-key --name $AcsResource --resource-group $ResourceGroup --query primaryConnectionString -o tsv
$speechKey = az cognitiveservices account keys list --name $SpeechResource --resource-group $ResourceGroup --query key1 -o tsv
$speechRegion = $Location

$openAIEndpoint = az cognitiveservices account show --name $OpenAIResource --resource-group $ResourceGroup --query properties.endpoint -o tsv
$openAIKey = az cognitiveservices account keys list --name $OpenAIResource --resource-group $ResourceGroup --query key1 -o tsv

$storageKey = az storage account keys list --resource-group $ResourceGroup --account-name $StorageAccountName --query "[0].value" -o tsv
$storageConnection = az storage account show-connection-string --resource-group $ResourceGroup --name $StorageAccountName --query connectionString -o tsv

$pgHost = az postgres flexible-server show --resource-group $ResourceGroup --name $PostgresServer --query fullyQualifiedDomainName -o tsv
$databaseUrl = "postgresql+psycopg://$PostgresAdminUser:$PostgresPasswordPlain@$pgHost:5432/$PostgresDb?sslmode=require"

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
foreach ($app in @($BackendApp, $Model1App, $Model2App, $AcsWorkerApp)) {
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

az containerapp update --name $AcsWorkerApp --resource-group $ResourceGroup --set-env-vars `
    ACS_CONNECTION_STRING=secretref:acs-connection-string `
    AZURE_STORAGE_CONNECTION_STRING=secretref:az-storage-connection `
    RECORDING_CONTAINER=recordings `
    BACKEND_INTERNAL_URL=$publicBaseUrl `
    ACS_WORKER_SHARED_SECRET=secretref:acs-worker-shared-secret `
    ACS_CALLBACK_URL="$publicBaseUrl/api/v1/acs/webhook" `
    ENVIRONMENT=development | Out-Null

Write-Section "Create Static Web App (if missing) and configure GitHub secrets"
$null = az staticwebapp show --name $StaticWebApp --resource-group $ResourceGroup 2>$null
if ($LASTEXITCODE -ne 0) {
    az staticwebapp create --name $StaticWebApp --resource-group $ResourceGroup --location $Location --sku Standard | Out-Null
}
$swaToken = az staticwebapp secrets list --name $StaticWebApp --resource-group $ResourceGroup --query properties.apiKey -o tsv
Ensure-GhSecret -Name "AZURE_STATIC_WEB_APPS_API_TOKEN" -Value $swaToken
Ensure-GhSecret -Name "BACKEND_DATABASE_URL" -Value $databaseUrl
Ensure-GhSecret -Name "JWT_SECRET" -Value $JwtSecret
Ensure-GhSecret -Name "DEV_BACKEND_HEALTH_URL" -Value "$publicBaseUrl/health"

if ($RunWorkflows) {
    Write-Section "Trigger GitHub workflows"
    gh workflow run infra-dev.yml --ref $Branch
    gh workflow run deploy-dev.yml --ref $Branch
}

Write-Section "Done"
Write-Host "Backend URL: $publicBaseUrl"
Write-Host "Model1 URL (internal): $model1Url"
Write-Host "Model2 URL (internal): $model2Url"
Write-Host "ACS Worker URL (internal): $workerUrl"
Write-Host "Frontend origin configured: $FrontendOrigin"
Write-Host ""
Write-Host "Next:"
Write-Host "1) Ensure branch '$Branch' has your deployment changes."
Write-Host "2) Run deploy-dev workflow if not triggered."
Write-Host "3) Verify $publicBaseUrl/health returns 200."
