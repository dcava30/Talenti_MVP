param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$TenantId = "",
    [string]$Repo = "dcava30/Talenti_MVP",
    [ValidateSet("dev", "uat", "prod")]
    [string[]]$EnvironmentNames = @("dev", "uat", "prod"),
    [string]$Location = "australiaeast",
    [string]$AlertEmailAddress = "",
    [string]$PostgresAdminPassword = "",
    [string]$BackendDatabaseUrl = "",
    [string]$JwtSecret = "",
    [string]$Model1ImageRef = "",
    [string]$Model2ImageRef = "",
    [string]$FrontEndAllowedCidrs = ""
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

function Ensure-GhEnvironment {
    param(
        [string]$RepoName,
        [string]$EnvironmentName
    )

    gh api --method PUT -H "Accept: application/vnd.github+json" "repos/$RepoName/environments/$EnvironmentName" | Out-Null
}

function Ensure-GhWorkflowPermissions {
    param([string]$RepoName)

    gh api --method PUT `
        -H "Accept: application/vnd.github+json" `
        "repos/$RepoName/actions/permissions/workflow" `
        -f default_workflow_permissions=read `
        -F can_approve_pull_request_reviews=false | Out-Null
}

function Ensure-GhEnvironmentSecret {
    param(
        [string]$RepoName,
        [string]$EnvironmentName,
        [string]$Name,
        [string]$Value
    )

    gh secret set $Name --repo $RepoName --env $EnvironmentName --body $Value | Out-Null
}

function Ensure-GhEnvironmentVariable {
    param(
        [string]$RepoName,
        [string]$EnvironmentName,
        [string]$Name,
        [string]$Value
    )

    gh variable set $Name --repo $RepoName --env $EnvironmentName --body $Value | Out-Null
}

function Resolve-TenantId {
    param([string]$Subscription)

    $resolvedTenant = az account show --subscription $Subscription --query tenantId -o tsv
    if (-not $resolvedTenant) {
        throw "Unable to resolve tenant id for subscription '$Subscription'."
    }

    return $resolvedTenant
}

function Normalize-CidrJson {
    param([string]$Value)

    try {
        $parsed = $Value | ConvertFrom-Json
    } catch {
        throw "FrontEndAllowedCidrs must be a JSON array string such as [""203.0.113.0/24"",""198.51.100.0/24""]."
    }

    if (-not ($parsed -is [System.Array])) {
        throw "FrontEndAllowedCidrs must be a JSON array string such as [""203.0.113.0/24"",""198.51.100.0/24""]."
    }

    foreach ($cidr in $parsed) {
        if (-not ($cidr -is [string])) {
            throw "FrontEndAllowedCidrs must contain only CIDR strings."
        }
    }

    return ($parsed | ConvertTo-Json -Compress)
}

function Get-EnvironmentSettings {
    param(
        [ValidateSet("dev", "uat", "prod")]
        [string]$EnvironmentName,
        [string]$AzureLocation
    )

    switch ($EnvironmentName) {
        "dev" {
            return [ordered]@{
                AzureLocation = $AzureLocation
                ResourceGroup = "rg-talenti-dev-aue"
                AcrName = "acrtalentidev"
                KeyVaultName = "kv-talenti-dev-aue"
                FrontendStorageAccount = "sttalentidevaue"
                StaticWebAppName = "swa-talenti-dev-aue"
                BackendApp = "ca-backend-dev"
                BackendWorkerApp = "ca-backend-worker-dev"
                Model1App = "ca-model1-dev"
                Model2App = "ca-model2-dev"
                AcsWorkerApp = "ca-acs-worker-dev"
                OidcAppName = "gh-talenti-dev-oidc"
            }
        }
        "uat" {
            return [ordered]@{
                AzureLocation = $AzureLocation
                ResourceGroup = "rg-talenti-uat-aue"
                AcrName = "acrtalentiuat"
                KeyVaultName = "kv-talenti-uat-aue"
                FrontendStorageAccount = "sttalentiuataue"
                StaticWebAppName = "swa-talenti-uat-aue"
                FrontDoorProfileName = "fdp-talenti-uat-aue"
                FrontDoorEndpointName = "afd-talenti-uat-aue"
                BackendApp = "ca-backend-uat"
                BackendWorkerApp = "ca-backend-worker-uat"
                Model1App = "ca-model1-uat"
                Model2App = "ca-model2-uat"
                AcsWorkerApp = "ca-acs-worker-uat"
                OidcAppName = "gh-talenti-uat-oidc"
            }
        }
        "prod" {
            return [ordered]@{
                AzureLocation = $AzureLocation
                ResourceGroup = "rg-talenti-prod-aue"
                AcrName = "acrtalentiprod"
                KeyVaultName = "kv-talenti-prod-aue"
                FrontendStorageAccount = "sttalentiprodaue"
                StaticWebAppName = "swa-talenti-prod-aue"
                FrontDoorProfileName = "fdp-talenti-prod-aue"
                FrontDoorEndpointName = "afd-talenti-prod-aue"
                BackendApp = "ca-backend-prod"
                BackendWorkerApp = "ca-backend-worker-prod"
                Model1App = "ca-model1-prod"
                Model2App = "ca-model2-prod"
                AcsWorkerApp = "ca-acs-worker-prod"
                OidcAppName = "gh-talenti-prod-oidc"
            }
        }
    }
}

function Ensure-OidcIdentity {
    param(
        [System.Collections.IDictionary]$Settings,
        [string]$EnvironmentName,
        [string]$RepoName
    )

    $oidcAppId = az ad app list --display-name $Settings.OidcAppName --query "[0].appId" -o tsv
    if (-not $oidcAppId) {
        $oidcAppId = az ad app create --display-name $Settings.OidcAppName --query appId -o tsv
    }

    $spObjectId = az ad sp list --filter "appId eq '$oidcAppId'" --query "[0].id" -o tsv
    if (-not $spObjectId) {
        $spObjectId = az ad sp create --id $oidcAppId --query id -o tsv
    }

    $rgId = az group show --name $Settings.ResourceGroup --query id -o tsv
    Ensure-AzRoleAssignment -PrincipalId $spObjectId -Role "Contributor" -Scope $rgId
    Ensure-AzRoleAssignment -PrincipalId $spObjectId -Role "User Access Administrator" -Scope $rgId

    $federatedName = "github-$EnvironmentName"
    $existingFederated = az ad app federated-credential list --id $oidcAppId --query "[?name=='$federatedName'].name | [0]" -o tsv
    if (-not $existingFederated) {
        $subject = "repo:${RepoName}:environment:${EnvironmentName}"
        $tmpFed = Join-Path $env:TEMP "talenti-fed-$([guid]::NewGuid().ToString('N')).json"
        @"
{
  "name": "$federatedName",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "$subject",
  "audiences": [ "api://AzureADTokenExchange" ]
}
"@ | Set-Content -Path $tmpFed -Encoding UTF8
        az ad app federated-credential create --id $oidcAppId --parameters $tmpFed | Out-Null
        Remove-Item $tmpFed -Force
    }

    return $oidcAppId
}

if ($EnvironmentNames.Count -gt 1 -and ($PostgresAdminPassword -or $BackendDatabaseUrl -or $JwtSecret)) {
    throw "POSTGRES_ADMIN_PASSWORD, BACKEND_DATABASE_URL, and JWT_SECRET are environment-specific. Configure one environment at a time when setting those secrets."
}

Require-Command "az"
Require-Command "gh"

$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run 'gh auth login' and rerun."
}

Write-Section "Configure GitHub Actions permissions baseline"
Ensure-GhWorkflowPermissions -RepoName $Repo
Write-Host "For branch protection and merge policy enforcement, run scripts/harden-github-governance.ps1."

Write-Section "Resolve Azure account context"
az account set --subscription $SubscriptionId
if (-not $TenantId) {
    $TenantId = Resolve-TenantId -Subscription $SubscriptionId
}

$normalizedFrontEndAllowedCidrs = ""
if ($FrontEndAllowedCidrs) {
    $normalizedFrontEndAllowedCidrs = Normalize-CidrJson -Value $FrontEndAllowedCidrs
}

$pendingByEnvironment = @{}

foreach ($environmentName in $EnvironmentNames) {
    $settings = Get-EnvironmentSettings -EnvironmentName $environmentName -AzureLocation $Location
    $pending = New-Object System.Collections.Generic.List[string]
    $pendingByEnvironment[$environmentName] = $pending

    Write-Section "Configure GitHub environment '$environmentName'"
    Ensure-GhEnvironment -RepoName $Repo -EnvironmentName $environmentName

    az group create --name $settings.ResourceGroup --location $settings.AzureLocation | Out-Null
    $oidcAppId = Ensure-OidcIdentity -Settings $settings -EnvironmentName $environmentName -RepoName $Repo

    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "AZURE_LOCATION" -Value $settings.AzureLocation
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "AZURE_RESOURCE_GROUP" -Value $settings.ResourceGroup
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "ACR_NAME" -Value $settings.AcrName
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "KEY_VAULT_NAME" -Value $settings.KeyVaultName
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "BACKEND_APP" -Value $settings.BackendApp
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "BACKEND_WORKER_APP" -Value $settings.BackendWorkerApp
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "MODEL1_APP" -Value $settings.Model1App
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "MODEL2_APP" -Value $settings.Model2App
    Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "ACS_WORKER_APP" -Value $settings.AcsWorkerApp

    if ($environmentName -eq "dev") {
        Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "STATIC_WEB_APP_NAME" -Value $settings.StaticWebAppName
    } else {
        Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "FRONTEND_STORAGE_ACCOUNT" -Value $settings.FrontendStorageAccount
        Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "FRONT_DOOR_PROFILE_NAME" -Value $settings.FrontDoorProfileName
        Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "FRONT_DOOR_ENDPOINT_NAME" -Value $settings.FrontDoorEndpointName
    }

    if ($AlertEmailAddress) {
        Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "ALERT_EMAIL_ADDRESS" -Value $AlertEmailAddress
    } else {
        $pending.Add("variable ALERT_EMAIL_ADDRESS")
    }

    if ($environmentName -eq "dev") {
        if ($Model1ImageRef) {
            Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "MODEL1_IMAGE_REF" -Value $Model1ImageRef
        } else {
            $pending.Add("variable MODEL1_IMAGE_REF")
        }

        if ($Model2ImageRef) {
            Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "MODEL2_IMAGE_REF" -Value $Model2ImageRef
        } else {
            $pending.Add("variable MODEL2_IMAGE_REF")
        }
    } elseif ($environmentName -eq "uat") {
        if ($normalizedFrontEndAllowedCidrs) {
            Ensure-GhEnvironmentVariable -RepoName $Repo -EnvironmentName $environmentName -Name "FRONTEND_ALLOWED_CIDRS" -Value $normalizedFrontEndAllowedCidrs
        } else {
            $pending.Add("variable FRONTEND_ALLOWED_CIDRS")
        }
    }

    Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "AZURE_CLIENT_ID" -Value $oidcAppId
    Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "AZURE_TENANT_ID" -Value $TenantId
    Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "AZURE_SUBSCRIPTION_ID" -Value $SubscriptionId

    if ($PostgresAdminPassword) {
        Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "POSTGRES_ADMIN_PASSWORD" -Value $PostgresAdminPassword
    } else {
        $pending.Add("secret POSTGRES_ADMIN_PASSWORD")
    }

    if ($BackendDatabaseUrl) {
        Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "BACKEND_DATABASE_URL" -Value $BackendDatabaseUrl
    } else {
        $pending.Add("secret BACKEND_DATABASE_URL")
    }

    if ($JwtSecret) {
        Ensure-GhEnvironmentSecret -RepoName $Repo -EnvironmentName $environmentName -Name "JWT_SECRET" -Value $JwtSecret
    } else {
        $pending.Add("secret JWT_SECRET")
    }

    Write-Host "OIDC app: $($settings.OidcAppName) ($oidcAppId)"
    Write-Host "Resource group: $($settings.ResourceGroup)"
}

Write-Section "Pending values"
$hasPending = $false
foreach ($environmentName in $EnvironmentNames) {
    $pendingItems = $pendingByEnvironment[$environmentName]
    if ($pendingItems.Count -eq 0) {
        continue
    }

    $hasPending = $true
    Write-Host "${environmentName}:"
    foreach ($item in $pendingItems) {
        Write-Host "- $item"
    }
}

if (-not $hasPending) {
    Write-Host "All requested variables and secrets were populated."
}

Write-Section "Done"
Write-Host "GitHub environments are configured for: $($EnvironmentNames -join ', ')"
