# Talenti Python Backend - Deployment Guide

> Complete step-by-step guide for deploying the Talenti Python FastAPI backend to Azure Container Apps with Infrastructure as Code and CI/CD pipelines.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Azure Resource Overview](#2-azure-resource-overview)
3. [Quick Start Deployment](#3-quick-start-deployment)
4. [Bicep Infrastructure Templates](#4-bicep-infrastructure-templates)
5. [GitHub Actions Workflows](#5-github-actions-workflows)
6. [Environment Configuration](#6-environment-configuration)
7. [Container Registry Setup](#7-container-registry-setup)
8. [Database & Storage Setup](#8-database--storage-setup)
9. [Networking & Security](#9-networking--security)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Scaling Configuration](#11-scaling-configuration)
12. [Disaster Recovery](#12-disaster-recovery)
13. [Troubleshooting Guide](#13-troubleshooting-guide)
14. [Cost Optimization](#14-cost-optimization)

---

## 1. Prerequisites

### 1.1 Required Tools

```bash
# Azure CLI (v2.50+)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az --version

# Bicep CLI (included with Azure CLI 2.20+)
az bicep install
az bicep version

# Docker (v24+)
docker --version

# GitHub CLI (optional, for workflow management)
gh --version
```

### 1.2 Azure Account Setup

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "<SUBSCRIPTION_ID>"

# Verify subscription
az account show --query "{name:name, id:id}" -o table

# Register required providers
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Communication

# Check registration status
az provider show -n Microsoft.App --query "registrationState" -o tsv
```

### 1.3 Required Permissions

| Role | Scope | Purpose |
|------|-------|---------|
| Contributor | Resource Group | Create/manage resources |
| Key Vault Administrator | Key Vault | Manage secrets |
| AcrPush | Container Registry | Push container images |
| User Access Administrator | Resource Group | Assign managed identities |

### 1.4 GitHub Repository Setup

```bash
# Required repository secrets
AZURE_CREDENTIALS          # Service principal JSON
AZURE_SUBSCRIPTION_ID      # Azure subscription ID
AZURE_RESOURCE_GROUP       # Target resource group name
ACR_LOGIN_SERVER          # Container registry URL
ACR_USERNAME              # Registry username (or use managed identity)
ACR_PASSWORD              # Registry password (or use managed identity)

# Application secrets (stored in Key Vault, referenced here)
DATABASE_URL
JWT_SECRET
JWT_ISSUER
JWT_AUDIENCE
AZURE_STORAGE_ACCOUNT
AZURE_STORAGE_ACCOUNT_KEY
AZURE_STORAGE_CONTAINER
AZURE_STORAGE_SAS_TTL_MINUTES
AZURE_ACS_CONNECTION_STRING
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_DEPLOYMENT
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
```

---

## 2. Azure Resource Overview

### 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Azure Resource Group                              │
│                          (rg-talenti-prod-aue)                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Container Apps Environment                         │   │
│  │                    (cae-talenti-prod-aue)                            │   │
│  │                                                                       │   │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │   │
│  │   │  API Container  │    │  Worker Container│    │ Redis Sidecar │  │   │
│  │   │  (ca-api-prod)  │    │  (ca-worker-prod)│    │  (Dapr State) │  │   │
│  │   │                 │    │                  │    │               │  │   │
│  │   │  FastAPI:8000   │    │  Celery Workers  │    │  Port: 6379   │  │   │
│  │   │  Replicas: 2-10 │    │  Replicas: 1-5   │    │               │  │   │
│  │   └────────┬────────┘    └────────┬─────────┘    └───────────────┘  │   │
│  │            │                      │                                  │   │
│  │   ┌────────┴──────────────────────┴─────────┐                       │   │
│  │   │          Internal Virtual Network        │                       │   │
│  │   │          (10.0.0.0/16)                  │                       │   │
│  │   └──────────────────────────────────────────┘                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Key Vault  │  │     ACR      │  │ Log Analytics│  │ App Insights │    │
│  │ (kv-talenti) │  │(acrtalenti)  │  │ (law-talenti)│  │(appi-talenti)│    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Azure OpenAI │  │ Azure Speech │  │   Azure ACS  │  │ Blob Storage │    │
│  │(oai-talenti) │  │(speech-tal)  │  │ (acs-talenti)│  │ (sttalenti)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Resource Naming Convention

```
{resource-type}-{app-name}-{environment}-{region}

Examples:
- rg-talenti-prod-aue         (Resource Group)
- cae-talenti-prod-aue        (Container Apps Environment)
- ca-api-talenti-prod-aue     (Container App - API)
- ca-worker-talenti-prod-aue  (Container App - Worker)
- acr-talenti-prod            (Container Registry - global)
- kv-talenti-prod-aue         (Key Vault)
- law-talenti-prod-aue        (Log Analytics Workspace)
- appi-talenti-prod-aue       (Application Insights)
- st-talenti-prod-aue         (Storage Account)
```

### 2.3 Environment Tiers

| Environment | SKU/Tier | Replicas | Purpose |
|-------------|----------|----------|---------|
| Development | Consumption | 1 | Feature development |
| Staging | Consumption | 1-2 | Pre-production testing |
| Production | Workload Profiles | 2-10 | Live traffic |

---

## 3. Quick Start Deployment

### 3.1 One-Command Deployment

```bash
# Clone repository
git clone https://github.com/your-org/talenti-python-backend.git
cd talenti-python-backend

# Set environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_LOCATION="australiaeast"
export ENVIRONMENT="prod"

# Deploy everything
./scripts/deploy.sh --env $ENVIRONMENT --location $AZURE_LOCATION
```

### 3.2 Step-by-Step Manual Deployment

```bash
# 1. Create resource group
az group create \
  --name "rg-talenti-${ENVIRONMENT}-aue" \
  --location "$AZURE_LOCATION" \
  --tags "project=talenti" "environment=${ENVIRONMENT}"

# 2. Deploy infrastructure with Bicep
az deployment group create \
  --resource-group "rg-talenti-${ENVIRONMENT}-aue" \
  --template-file ./infra/main.bicep \
  --parameters environment="${ENVIRONMENT}" \
  --parameters location="${AZURE_LOCATION}"

# 3. Build and push container image
az acr build \
  --registry "acrtalenti${ENVIRONMENT}" \
  --image "talenti-api:latest" \
  --file ./Dockerfile .

# 4. Deploy container app
az containerapp update \
  --name "ca-api-talenti-${ENVIRONMENT}-aue" \
  --resource-group "rg-talenti-${ENVIRONMENT}-aue" \
  --image "acrtalenti${ENVIRONMENT}.azurecr.io/talenti-api:latest"

# 5. Verify deployment
az containerapp show \
  --name "ca-api-talenti-${ENVIRONMENT}-aue" \
  --resource-group "rg-talenti-${ENVIRONMENT}-aue" \
  --query "properties.latestRevisionFqdn" -o tsv
```

---

## 4. Bicep Infrastructure Templates

### 4.1 Project Structure

```
infra/
├── main.bicep                    # Main deployment orchestrator
├── parameters/
│   ├── dev.bicepparam           # Development parameters
│   ├── staging.bicepparam       # Staging parameters
│   └── prod.bicepparam          # Production parameters
├── modules/
│   ├── container-registry.bicep  # ACR module
│   ├── container-apps-env.bicep  # Container Apps Environment
│   ├── container-app.bicep       # Container App definition
│   ├── key-vault.bicep          # Key Vault with secrets
│   ├── log-analytics.bicep      # Logging infrastructure
│   ├── app-insights.bicep       # Application Insights
│   ├── storage.bicep            # Blob Storage
│   ├── cognitive-services.bicep # Azure OpenAI + Speech
│   ├── communication.bicep      # Azure Communication Services
│   └── networking.bicep         # VNet and NSGs
└── scripts/
    ├── deploy.sh                # Deployment script
    ├── validate.sh              # Template validation
    └── destroy.sh               # Resource cleanup
```

### 4.2 Main Orchestrator (main.bicep)

```bicep
// infra/main.bicep
// Main deployment template for Talenti Python Backend

targetScope = 'resourceGroup'

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region for deployment')
param location string = resourceGroup().location

@description('Base name for resources')
param appName string = 'talenti'

@description('Container image tag')
param imageTag string = 'latest'

@description('Enable zone redundancy (prod only)')
param zoneRedundant bool = environment == 'prod'

@description('Database configuration')
@secure()
param databaseUrl string

@description('JWT configuration')
@secure()
param jwtSecret string

param jwtIssuer string = 'talenti'
param jwtAudience string = 'talenti-users'

@description('Azure Storage configuration')
@secure()
param storageAccount string

@secure()
param storageAccountKey string

@secure()
param storageContainer string

param storageSasTtlMinutes int = 15

@description('Azure OpenAI configuration')
@secure()
param azureOpenAIEndpoint string

@secure()
param azureOpenAIKey string

@description('Azure Speech configuration')
@secure()
param azureSpeechKey string

param azureSpeechRegion string = 'australiaeast'

@description('Azure Communication Services connection string')
@secure()
param acsConnectionString string

// ============================================================================
// VARIABLES
// ============================================================================

var resourcePrefix = '${appName}-${environment}'
var locationShort = 'aue' // Australia East

var tags = {
  project: appName
  environment: environment
  managedBy: 'bicep'
  deployedAt: utcNow('yyyy-MM-ddTHH:mm:ssZ')
}

// Container configuration per environment
var containerConfig = {
  dev: {
    cpu: '0.5'
    memory: '1Gi'
    minReplicas: 1
    maxReplicas: 2
  }
  staging: {
    cpu: '0.5'
    memory: '1Gi'
    minReplicas: 1
    maxReplicas: 3
  }
  prod: {
    cpu: '1'
    memory: '2Gi'
    minReplicas: 2
    maxReplicas: 10
  }
}

// ============================================================================
// MODULES
// ============================================================================

// Log Analytics Workspace
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics-${uniqueString(deployment().name)}'
  params: {
    name: 'law-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    retentionInDays: environment == 'prod' ? 90 : 30
  }
}

// Application Insights
module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights-${uniqueString(deployment().name)}'
  params: {
    name: 'appi-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    workspaceId: logAnalytics.outputs.workspaceId
  }
}

// Key Vault
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault-${uniqueString(deployment().name)}'
  params: {
    name: 'kv-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    secrets: [
      { name: 'database-url', value: databaseUrl }
      { name: 'jwt-secret', value: jwtSecret }
      { name: 'jwt-issuer', value: jwtIssuer }
      { name: 'jwt-audience', value: jwtAudience }
      { name: 'azure-storage-account', value: storageAccount }
      { name: 'azure-storage-account-key', value: storageAccountKey }
      { name: 'azure-storage-container', value: storageContainer }
      { name: 'azure-storage-sas-ttl', value: string(storageSasTtlMinutes) }
      { name: 'azure-openai-endpoint', value: azureOpenAIEndpoint }
      { name: 'azure-openai-key', value: azureOpenAIKey }
      { name: 'azure-speech-key', value: azureSpeechKey }
      { name: 'acs-connection-string', value: acsConnectionString }
    ]
  }
}

// Container Registry
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry-${uniqueString(deployment().name)}'
  params: {
    name: 'acr${appName}${environment}'
    location: location
    tags: tags
    sku: environment == 'prod' ? 'Premium' : 'Basic'
    adminUserEnabled: false
    zoneRedundancy: zoneRedundant
  }
}

// Storage Account
module storage 'modules/storage.bicep' = {
  name: 'storage-${uniqueString(deployment().name)}'
  params: {
    name: 'st${appName}${environment}${locationShort}'
    location: location
    tags: tags
    sku: environment == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'
    containers: [
      { name: 'interview-recordings', publicAccess: 'None' }
      { name: 'candidate-documents', publicAccess: 'None' }
      { name: 'exports', publicAccess: 'None' }
    ]
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv-${uniqueString(deployment().name)}'
  params: {
    name: 'cae-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    appInsightsConnectionString: appInsights.outputs.connectionString
    zoneRedundant: zoneRedundant
  }
}

// API Container App
module apiContainerApp 'modules/container-app.bicep' = {
  name: 'apiContainerApp-${uniqueString(deployment().name)}'
  params: {
    name: 'ca-api-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: containerRegistry.outputs.name
    imageName: 'talenti-api'
    imageTag: imageTag
    targetPort: 8000
    cpu: containerConfig[environment].cpu
    memory: containerConfig[environment].memory
    minReplicas: containerConfig[environment].minReplicas
    maxReplicas: containerConfig[environment].maxReplicas
    
    // Environment variables
    envVars: [
      { name: 'ENVIRONMENT', value: environment }
      { name: 'LOG_LEVEL', value: environment == 'prod' ? 'INFO' : 'DEBUG' }
      { name: 'AZURE_SPEECH_REGION', value: azureSpeechRegion }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.outputs.connectionString }
    ]
    
    // Secret references from Key Vault
    secretRefs: [
      { name: 'database-url', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/database-url' }
      { name: 'jwt-secret', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-secret' }
      { name: 'jwt-issuer', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-issuer' }
      { name: 'jwt-audience', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-audience' }
      { name: 'azure-storage-account', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-account' }
      { name: 'azure-storage-account-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-account-key' }
      { name: 'azure-storage-container', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-container' }
      { name: 'azure-storage-sas-ttl', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-sas-ttl' }
      { name: 'azure-openai-endpoint', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-openai-endpoint' }
      { name: 'azure-openai-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-openai-key' }
      { name: 'azure-speech-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-speech-key' }
      { name: 'acs-connection-string', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/acs-connection-string' }
    ]
    
    // Health probes
    livenessProbe: {
      httpGet: {
        path: '/health'
        port: 8000
      }
      initialDelaySeconds: 10
      periodSeconds: 30
    }
    readinessProbe: {
      httpGet: {
        path: '/health'
        port: 8000
      }
      initialDelaySeconds: 5
      periodSeconds: 10
    }
    
    // Ingress configuration
    ingressEnabled: true
    ingressExternal: true
    corsPolicy: {
      allowedOrigins: environment == 'prod' 
        ? ['https://talenti.app', 'https://www.talenti.app']
        : ['*']
      allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
      allowedHeaders: ['*']
      allowCredentials: true
    }
  }
}

// Worker Container App (for background jobs)
module workerContainerApp 'modules/container-app.bicep' = {
  name: 'workerContainerApp-${uniqueString(deployment().name)}'
  params: {
    name: 'ca-worker-${resourcePrefix}-${locationShort}'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: containerRegistry.outputs.name
    imageName: 'talenti-worker'
    imageTag: imageTag
    targetPort: 8001
    cpu: '0.5'
    memory: '1Gi'
    minReplicas: 1
    maxReplicas: environment == 'prod' ? 5 : 2
    
    envVars: [
      { name: 'ENVIRONMENT', value: environment }
      { name: 'LOG_LEVEL', value: 'INFO' }
      { name: 'WORKER_MODE', value: 'true' }
    ]
    
    secretRefs: [
      { name: 'database-url', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/database-url' }
      { name: 'jwt-secret', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-secret' }
      { name: 'jwt-issuer', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-issuer' }
      { name: 'jwt-audience', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/jwt-audience' }
      { name: 'azure-storage-account', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-account' }
      { name: 'azure-storage-account-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-account-key' }
      { name: 'azure-storage-container', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-container' }
      { name: 'azure-storage-sas-ttl', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-storage-sas-ttl' }
      { name: 'azure-openai-endpoint', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-openai-endpoint' }
      { name: 'azure-openai-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-openai-key' }
      { name: 'azure-speech-key', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/azure-speech-key' }
      { name: 'acs-connection-string', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/acs-connection-string' }
    ]
    
    ingressEnabled: false
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

output resourceGroupName string = resourceGroup().name
output containerAppFqdn string = apiContainerApp.outputs.fqdn
output containerAppUrl string = 'https://${apiContainerApp.outputs.fqdn}'
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output logAnalyticsWorkspaceId string = logAnalytics.outputs.workspaceId
output appInsightsConnectionString string = appInsights.outputs.connectionString
output storageAccountName string = storage.outputs.name
```

### 4.3 Container Apps Environment Module

```bicep
// infra/modules/container-apps-env.bicep

@description('Container Apps Environment name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Enable zone redundancy')
param zoneRedundant bool = false

@description('Workload profile configuration')
param workloadProfiles array = []

// Get Log Analytics workspace key
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: last(split(logAnalyticsWorkspaceId, '/'))
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-11-02-preview' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: appInsightsConnectionString
    zoneRedundant: zoneRedundant
    
    // Workload profiles for production
    workloadProfiles: !empty(workloadProfiles) ? workloadProfiles : [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    
    // Infrastructure subnet (optional, for VNet integration)
    // infrastructureSubnetId: subnetId
    
    peerAuthentication: {
      mtls: {
        enabled: true
      }
    }
  }
}

// Dapr component for Redis state store (optional)
resource daprRedis 'Microsoft.App/managedEnvironments/daprComponents@2023-11-02-preview' = {
  parent: containerAppsEnvironment
  name: 'statestore'
  properties: {
    componentType: 'state.redis'
    version: 'v1'
    metadata: [
      {
        name: 'redisHost'
        value: 'redis:6379'
      }
      {
        name: 'actorStateStore'
        value: 'true'
      }
    ]
    scopes: [
      'ca-api-*'
    ]
  }
}

output environmentId string = containerAppsEnvironment.id
output environmentName string = containerAppsEnvironment.name
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output staticIp string = containerAppsEnvironment.properties.staticIp
```

### 4.4 Container App Module

```bicep
// infra/modules/container-app.bicep

@description('Container App name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment ID')
param containerAppsEnvironmentId string

@description('Container Registry name')
param containerRegistryName string

@description('Container image name')
param imageName string

@description('Container image tag')
param imageTag string = 'latest'

@description('Container port')
param targetPort int = 8000

@description('CPU allocation')
param cpu string = '0.5'

@description('Memory allocation')
param memory string = '1Gi'

@description('Minimum replicas')
@minValue(0)
@maxValue(30)
param minReplicas int = 1

@description('Maximum replicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 10

@description('Environment variables')
param envVars array = []

@description('Secret references from Key Vault')
param secretRefs array = []

@description('Liveness probe configuration')
param livenessProbe object = {}

@description('Readiness probe configuration')
param readinessProbe object = {}

@description('Enable ingress')
param ingressEnabled bool = true

@description('External ingress')
param ingressExternal bool = true

@description('CORS policy')
param corsPolicy object = {}

// Reference container registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: containerRegistryName
}

// User-assigned managed identity for Key Vault access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${name}'
  location: location
  tags: tags
}

// Build secrets array from Key Vault references
var secrets = [for secret in secretRefs: {
  name: secret.name
  keyVaultUrl: secret.keyVaultUrl
  identity: managedIdentity.id
}]

// Build environment variables with secret references
var envVarsWithSecrets = concat(envVars, [for secret in secretRefs: {
  name: replace(toUpper(secret.name), '-', '_')
  secretRef: secret.name
}])

resource containerApp 'Microsoft.App/containerApps@2023-11-02-preview' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    
    configuration: {
      activeRevisionsMode: 'Multiple'
      
      // Container registry authentication
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      
      // Secrets from Key Vault
      secrets: secrets
      
      // Ingress configuration
      ingress: ingressEnabled ? {
        external: ingressExternal
        targetPort: targetPort
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        corsPolicy: !empty(corsPolicy) ? corsPolicy : null
      } : null
      
      // Dapr configuration (optional)
      dapr: {
        enabled: false
        appId: name
        appPort: targetPort
        appProtocol: 'http'
      }
    }
    
    template: {
      containers: [
        {
          name: 'main'
          image: '${containerRegistry.properties.loginServer}/${imageName}:${imageTag}'
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: envVarsWithSecrets
          probes: concat(
            !empty(livenessProbe) ? [{ type: 'Liveness', ...livenessProbe }] : [],
            !empty(readinessProbe) ? [{ type: 'Readiness', ...readinessProbe }] : []
          )
        }
      ]
      
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
          {
            name: 'cpu-scaling'
            custom: {
              type: 'cpu'
              metadata: {
                type: 'Utilization'
                value: '70'
              }
            }
          }
        ]
      }
    }
  }
}

// Grant ACR pull permission to managed identity
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, managedIdentity.id, 'acrpull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output id string = containerApp.id
output name string = containerApp.name
output fqdn string = ingressEnabled ? containerApp.properties.configuration.ingress.fqdn : ''
output latestRevisionName string = containerApp.properties.latestRevisionName
output managedIdentityId string = managedIdentity.id
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
```

### 4.5 Key Vault Module

```bicep
// infra/modules/key-vault.bicep

@description('Key Vault name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Secrets to create')
@secure()
param secrets array = []

@description('Enable soft delete')
param enableSoftDelete bool = true

@description('Soft delete retention days')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Enable purge protection')
param enablePurgeProtection bool = true

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    
    enabledForDeployment: true
    enabledForDiskEncryption: true
    enabledForTemplateDeployment: true
    
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection
    
    enableRbacAuthorization: true
    
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

// Create secrets
resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for secret in secrets: {
  parent: keyVault
  name: secret.name
  properties: {
    value: secret.value
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}]

output vaultUri string = keyVault.properties.vaultUri
output name string = keyVault.name
output id string = keyVault.id
```

### 4.6 Storage Module

```bicep
// infra/modules/storage.bicep

@description('Storage account name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Storage SKU')
@allowed(['Standard_LRS', 'Standard_GRS', 'Standard_ZRS', 'Standard_RAGRS'])
param sku string = 'Standard_LRS'

@description('Blob containers to create')
param containers array = []

@description('Enable hierarchical namespace (Data Lake)')
param enableHns bool = false

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    isHnsEnabled: enableHns
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    
    encryption: {
      services: {
        blob: { enabled: true }
        file: { enabled: true }
      }
      keySource: 'Microsoft.Storage'
    }
    
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for container in containers: {
  parent: blobService
  name: container.name
  properties: {
    publicAccess: container.publicAccess
  }
}]

output name string = storageAccount.name
output id string = storageAccount.id
output primaryEndpoints object = storageAccount.properties.primaryEndpoints
output connectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
```

### 4.7 Production Parameters

```bicep
// infra/parameters/prod.bicepparam
using '../main.bicep'

param environment = 'prod'
param location = 'australiaeast'
param imageTag = 'latest'
param zoneRedundant = true

// Secrets passed via GitHub Actions or Key Vault
param databaseUrl = readEnvironmentVariable('DATABASE_URL')
param jwtSecret = readEnvironmentVariable('JWT_SECRET')
param jwtIssuer = readEnvironmentVariable('JWT_ISSUER')
param jwtAudience = readEnvironmentVariable('JWT_AUDIENCE')
param storageAccount = readEnvironmentVariable('AZURE_STORAGE_ACCOUNT')
param storageAccountKey = readEnvironmentVariable('AZURE_STORAGE_ACCOUNT_KEY')
param storageContainer = readEnvironmentVariable('AZURE_STORAGE_CONTAINER')
param storageSasTtlMinutes = int(readEnvironmentVariable('AZURE_STORAGE_SAS_TTL_MINUTES'))
param azureOpenAIEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT')
param azureOpenAIKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY')
param azureSpeechKey = readEnvironmentVariable('AZURE_SPEECH_KEY')
param acsConnectionString = readEnvironmentVariable('AZURE_ACS_CONNECTION_STRING')
```

---

## 5. GitHub Actions Workflows

### 5.1 Workflow Structure

```
.github/
├── workflows/
│   ├── ci.yml                    # Continuous Integration
│   ├── cd-dev.yml                # Deploy to Development
│   ├── cd-staging.yml            # Deploy to Staging
│   ├── cd-prod.yml               # Deploy to Production
│   ├── infrastructure.yml        # Infrastructure deployment
│   └── security-scan.yml         # Security scanning
├── actions/
│   ├── build-push/
│   │   └── action.yml           # Reusable build action
│   └── deploy-container-app/
│       └── action.yml           # Reusable deploy action
└── CODEOWNERS
```

### 5.2 CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI - Build and Test

on:
  push:
    branches: [main, develop]
    paths:
      - 'app/**'
      - 'tests/**'
      - 'requirements.txt'
      - 'Dockerfile'
      - '.github/workflows/ci.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'app/**'
      - 'tests/**'
      - 'requirements.txt'
      - 'Dockerfile'

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ============================================
  # LINT AND FORMAT CHECK
  # ============================================
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install linting tools
        run: |
          python -m pip install --upgrade pip
          pip install ruff black isort mypy

      - name: Run Ruff linter
        run: ruff check app/ tests/

      - name: Check Black formatting
        run: black --check app/ tests/

      - name: Check import sorting
        run: isort --check-only app/ tests/

      - name: Run type checking
        run: mypy app/ --ignore-missing-imports

  # ============================================
  # UNIT TESTS
  # ============================================
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio httpx

      - name: Run tests with coverage
        run: |
          pytest tests/ \
            --cov=app \
            --cov-report=xml \
            --cov-report=html \
            --cov-fail-under=80 \
            -v
        env:
          ENVIRONMENT: test
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Upload coverage HTML report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/

  # ============================================
  # SECURITY SCAN
  # ============================================
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: lint
    permissions:
      security-events: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r app/ -f json -o bandit-report.json || true
          
      - name: Upload Bandit report
        uses: actions/upload-artifact@v4
        with:
          name: bandit-report
          path: bandit-report.json

  # ============================================
  # BUILD DOCKER IMAGE
  # ============================================
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [test, security]
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-tag: ${{ steps.meta.outputs.version }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix=
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            GIT_SHA=${{ github.sha }}
            VERSION=${{ steps.meta.outputs.version }}

      - name: Run Trivy on built image
        if: github.event_name != 'pull_request'
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}'
          format: 'table'
          exit-code: '1'
          ignore-unfixed: true
          severity: 'CRITICAL'
```

### 5.3 CD Production Workflow

```yaml
# .github/workflows/cd-prod.yml
name: CD - Deploy to Production

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image tag to deploy'
        required: true
        default: 'latest'
      skip_approval:
        description: 'Skip manual approval (emergency only)'
        required: false
        default: 'false'
        type: boolean
  push:
    tags:
      - 'v*.*.*'

concurrency:
  group: production-deployment
  cancel-in-progress: false

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  RESOURCE_GROUP: rg-talenti-prod-aue
  CONTAINER_APP_NAME: ca-api-talenti-prod-aue
  ACR_NAME: acrtalentiprod
  ENVIRONMENT: prod

jobs:
  # ============================================
  # PRE-DEPLOYMENT CHECKS
  # ============================================
  pre-deploy:
    name: Pre-deployment Checks
    runs-on: ubuntu-latest
    outputs:
      image-exists: ${{ steps.check-image.outputs.exists }}
      current-revision: ${{ steps.current-state.outputs.revision }}
    
    steps:
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Check image exists in ACR
        id: check-image
        run: |
          IMAGE_TAG="${{ github.event.inputs.image_tag || github.ref_name }}"
          
          EXISTS=$(az acr repository show-tags \
            --name ${{ env.ACR_NAME }} \
            --repository talenti-api \
            --query "contains(@, '${IMAGE_TAG}')" \
            --output tsv)
          
          echo "exists=${EXISTS}" >> $GITHUB_OUTPUT
          
          if [ "$EXISTS" != "true" ]; then
            echo "::error::Image tag ${IMAGE_TAG} not found in ACR"
            exit 1
          fi

      - name: Get current deployment state
        id: current-state
        run: |
          REVISION=$(az containerapp revision list \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "[?properties.active].name | [0]" \
            --output tsv)
          
          echo "revision=${REVISION}" >> $GITHUB_OUTPUT
          echo "Current active revision: ${REVISION}"

      - name: Run smoke tests on staging
        run: |
          STAGING_URL=$(az containerapp show \
            --name ca-api-talenti-staging-aue \
            --resource-group rg-talenti-staging-aue \
            --query "properties.configuration.ingress.fqdn" \
            --output tsv)
          
          # Health check
          HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${STAGING_URL}/health/ready")
          
          if [ "$HTTP_STATUS" != "200" ]; then
            echo "::error::Staging health check failed with status ${HTTP_STATUS}"
            exit 1
          fi
          
          echo "Staging health check passed"

  # ============================================
  # MANUAL APPROVAL
  # ============================================
  approval:
    name: Production Approval
    runs-on: ubuntu-latest
    needs: pre-deploy
    if: ${{ github.event.inputs.skip_approval != 'true' }}
    environment:
      name: production
      url: https://talenti.app
    
    steps:
      - name: Approval checkpoint
        run: echo "Deployment approved by ${{ github.actor }}"

  # ============================================
  # DEPLOY TO PRODUCTION
  # ============================================
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [pre-deploy, approval]
    if: always() && needs.pre-deploy.result == 'success' && (needs.approval.result == 'success' || needs.approval.result == 'skipped')
    environment:
      name: production
      url: https://talenti.app
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Get image tag
        id: image-tag
        run: |
          if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            echo "tag=${{ github.event.inputs.image_tag }}" >> $GITHUB_OUTPUT
          else
            # Extract version from tag (v1.2.3 -> 1.2.3)
            echo "tag=${GITHUB_REF_NAME#v}" >> $GITHUB_OUTPUT
          fi

      - name: Deploy new revision
        id: deploy
        run: |
          IMAGE="${{ env.ACR_NAME }}.azurecr.io/talenti-api:${{ steps.image-tag.outputs.tag }}"
          
          # Create new revision with 0% traffic
          az containerapp update \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image "${IMAGE}" \
            --revision-suffix "deploy-${{ github.run_number }}" \
            --set-env-vars "DEPLOY_SHA=${{ github.sha }}"
          
          # Get new revision name
          NEW_REVISION=$(az containerapp revision list \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "sort_by(@, &properties.createdTime)[-1].name" \
            --output tsv)
          
          echo "revision=${NEW_REVISION}" >> $GITHUB_OUTPUT
          echo "Deployed revision: ${NEW_REVISION}"

      - name: Health check new revision
        run: |
          FQDN=$(az containerapp show \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "properties.configuration.ingress.fqdn" \
            --output tsv)
          
          # Wait for revision to be ready
          echo "Waiting for revision to be ready..."
          sleep 30
          
          # Check health endpoint
          for i in {1..10}; do
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
              "https://${FQDN}/health/ready" \
              -H "X-Revision: ${{ steps.deploy.outputs.revision }}")
            
            if [ "$HTTP_STATUS" == "200" ]; then
              echo "Health check passed"
              exit 0
            fi
            
            echo "Attempt $i: Status ${HTTP_STATUS}, retrying..."
            sleep 10
          done
          
          echo "::error::Health check failed after 10 attempts"
          exit 1

      - name: Canary deployment (10% traffic)
        run: |
          az containerapp ingress traffic set \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --revision-weight \
              "${{ needs.pre-deploy.outputs.current-revision }}=90" \
              "${{ steps.deploy.outputs.revision }}=10"
          
          echo "Canary deployment: 10% traffic to new revision"

      - name: Monitor canary (5 minutes)
        run: |
          echo "Monitoring canary deployment for 5 minutes..."
          
          for i in {1..10}; do
            # Check error rate in App Insights
            # This is a simplified check - in production, query App Insights API
            
            FQDN=$(az containerapp show \
              --name ${{ env.CONTAINER_APP_NAME }} \
              --resource-group ${{ env.RESOURCE_GROUP }} \
              --query "properties.configuration.ingress.fqdn" \
              --output tsv)
            
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/health/ready")
            
            if [ "$HTTP_STATUS" != "200" ]; then
              echo "::warning::Health check returned ${HTTP_STATUS} during canary"
            fi
            
            sleep 30
          done
          
          echo "Canary monitoring complete"

      - name: Full rollout (100% traffic)
        run: |
          az containerapp ingress traffic set \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --revision-weight "${{ steps.deploy.outputs.revision }}=100"
          
          echo "Full rollout complete: 100% traffic to new revision"

      - name: Deactivate old revision
        run: |
          # Keep last 3 revisions, deactivate others
          REVISIONS=$(az containerapp revision list \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "sort_by(@, &properties.createdTime)[:-3].name" \
            --output tsv)
          
          for REV in $REVISIONS; do
            echo "Deactivating revision: ${REV}"
            az containerapp revision deactivate \
              --name ${{ env.CONTAINER_APP_NAME }} \
              --resource-group ${{ env.RESOURCE_GROUP }} \
              --revision "${REV}" || true
          done

      - name: Create deployment record
        run: |
          echo "## Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Property | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|----------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Environment | Production |" >> $GITHUB_STEP_SUMMARY
          echo "| Image Tag | ${{ steps.image-tag.outputs.tag }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Revision | ${{ steps.deploy.outputs.revision }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Deployed By | ${{ github.actor }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Commit SHA | ${{ github.sha }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Timestamp | $(date -u +"%Y-%m-%dT%H:%M:%SZ") |" >> $GITHUB_STEP_SUMMARY

  # ============================================
  # ROLLBACK (on failure)
  # ============================================
  rollback:
    name: Rollback on Failure
    runs-on: ubuntu-latest
    needs: [pre-deploy, deploy]
    if: failure() && needs.pre-deploy.outputs.current-revision != ''
    
    steps:
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Rollback to previous revision
        run: |
          echo "::warning::Deployment failed, rolling back..."
          
          az containerapp ingress traffic set \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --revision-weight "${{ needs.pre-deploy.outputs.current-revision }}=100"
          
          echo "Rolled back to revision: ${{ needs.pre-deploy.outputs.current-revision }}"

      - name: Notify rollback
        run: |
          echo "## ⚠️ Rollback Performed" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Deployment failed and was automatically rolled back." >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Rolled back to: ${{ needs.pre-deploy.outputs.current-revision }}" >> $GITHUB_STEP_SUMMARY

  # ============================================
  # POST-DEPLOYMENT
  # ============================================
  notify:
    name: Notify Deployment
    runs-on: ubuntu-latest
    needs: deploy
    if: always()
    
    steps:
      - name: Send Slack notification
        if: ${{ secrets.SLACK_WEBHOOK_URL }}
        uses: slackapi/slack-github-action@v1.26.0
        with:
          payload: |
            {
              "text": "${{ needs.deploy.result == 'success' && '✅' || '❌' }} Production Deployment ${{ needs.deploy.result }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment ${{ needs.deploy.result }}*\n\n• *Triggered by:* ${{ github.actor }}\n• *Commit:* `${{ github.sha }}`\n• *Workflow:* <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

### 5.4 Infrastructure Workflow

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure - Deploy Bicep

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - dev
          - staging
          - prod
      action:
        description: 'Deployment action'
        required: true
        type: choice
        options:
          - validate
          - what-if
          - deploy
  push:
    branches: [main]
    paths:
      - 'infra/**'
      - '.github/workflows/infrastructure.yml'

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

jobs:
  # ============================================
  # VALIDATE BICEP TEMPLATES
  # ============================================
  validate:
    name: Validate Templates
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Lint Bicep files
        run: |
          az bicep build --file infra/main.bicep --stdout > /dev/null
          echo "Bicep linting passed"

      - name: Validate template
        run: |
          ENVIRONMENT="${{ github.event.inputs.environment || 'dev' }}"
          RESOURCE_GROUP="rg-talenti-${ENVIRONMENT}-aue"
          
          az deployment group validate \
            --resource-group "${RESOURCE_GROUP}" \
            --template-file infra/main.bicep \
            --parameters @infra/parameters/${ENVIRONMENT}.bicepparam

  # ============================================
  # WHAT-IF ANALYSIS
  # ============================================
  what-if:
    name: What-If Analysis
    runs-on: ubuntu-latest
    needs: validate
    if: github.event.inputs.action == 'what-if' || github.event.inputs.action == 'deploy'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run What-If
        run: |
          ENVIRONMENT="${{ github.event.inputs.environment || 'dev' }}"
          RESOURCE_GROUP="rg-talenti-${ENVIRONMENT}-aue"
          
          az deployment group what-if \
            --resource-group "${RESOURCE_GROUP}" \
            --template-file infra/main.bicep \
            --parameters @infra/parameters/${ENVIRONMENT}.bicepparam

  # ============================================
  # DEPLOY INFRASTRUCTURE
  # ============================================
  deploy:
    name: Deploy Infrastructure
    runs-on: ubuntu-latest
    needs: what-if
    if: github.event.inputs.action == 'deploy'
    environment:
      name: ${{ github.event.inputs.environment }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Bicep template
        id: deploy
        run: |
          ENVIRONMENT="${{ github.event.inputs.environment }}"
          RESOURCE_GROUP="rg-talenti-${ENVIRONMENT}-aue"
          
          OUTPUTS=$(az deployment group create \
            --resource-group "${RESOURCE_GROUP}" \
            --template-file infra/main.bicep \
            --parameters @infra/parameters/${ENVIRONMENT}.bicepparam \
            --query "properties.outputs" \
            --output json)
          
          echo "outputs=${OUTPUTS}" >> $GITHUB_OUTPUT

      - name: Display outputs
        run: |
          echo "## Infrastructure Deployment Outputs" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo '```json' >> $GITHUB_STEP_SUMMARY
          echo '${{ steps.deploy.outputs.outputs }}' >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
```

---

## 6. Environment Configuration

### 6.1 Environment Variables Reference

```bash
# ===========================================
# REQUIRED - Azure Services
# ===========================================

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://oai-talenti-prod.openai.azure.com/
AZURE_OPENAI_API_KEY=<key-from-key-vault>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Speech Services
AZURE_SPEECH_KEY=<key-from-key-vault>
AZURE_SPEECH_REGION=australiaeast
AZURE_SPEECH_ENDPOINT=https://australiaeast.api.cognitive.microsoft.com/

# Azure Communication Services
AZURE_ACS_CONNECTION_STRING=endpoint=https://acs-talenti-prod.communication.azure.com/;accesskey=...

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT=sttalentiprodaue
AZURE_STORAGE_ACCOUNT_KEY=<storage-account-key>
AZURE_STORAGE_CONTAINER=interview-recordings
AZURE_STORAGE_SAS_TTL_MINUTES=15

# ===========================================
# REQUIRED - Database + Auth
# ===========================================

DATABASE_URL=sqlite:///./data/app.db
JWT_SECRET=<jwt-secret>
JWT_ISSUER=talenti
JWT_AUDIENCE=talenti-users

# ===========================================
# APPLICATION SETTINGS
# ===========================================

ENVIRONMENT=prod
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://talenti.app,https://www.talenti.app

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Recording retention
RECORDING_RETENTION_DAYS=30
MAX_RECORDING_DURATION_MINUTES=60

# ===========================================
# MONITORING
# ===========================================

APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
OTEL_SERVICE_NAME=talenti-api
OTEL_EXPORTER_OTLP_ENDPOINT=https://...

# ===========================================
# OPTIONAL - Redis (for rate limiting)
# ===========================================

REDIS_URL=redis://redis:6379
REDIS_PASSWORD=<optional>
```

### 6.2 Key Vault Secret Mapping

```bash
# Create secrets in Key Vault
az keyvault secret set --vault-name kv-talenti-prod-aue --name database-url --value "$DATABASE_URL"
az keyvault secret set --vault-name kv-talenti-prod-aue --name jwt-secret --value "$JWT_SECRET"
az keyvault secret set --vault-name kv-talenti-prod-aue --name jwt-issuer --value "$JWT_ISSUER"
az keyvault secret set --vault-name kv-talenti-prod-aue --name jwt-audience --value "$JWT_AUDIENCE"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-storage-account --value "$AZURE_STORAGE_ACCOUNT"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-storage-account-key --value "$AZURE_STORAGE_ACCOUNT_KEY"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-storage-container --value "$AZURE_STORAGE_CONTAINER"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-openai-endpoint --value "$AZURE_OPENAI_ENDPOINT"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-openai-key --value "$AZURE_OPENAI_API_KEY"
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-speech-key --value "$AZURE_SPEECH_KEY"
az keyvault secret set --vault-name kv-talenti-prod-aue --name acs-connection-string --value "$ACS_CONNECTION_STRING"

# List secrets
az keyvault secret list --vault-name kv-talenti-prod-aue --query "[].name" -o table
```

---

## 7. Container Registry Setup

### 7.1 Create Azure Container Registry

```bash
# Create ACR
az acr create \
  --resource-group rg-talenti-prod-aue \
  --name acrtalentiprod \
  --sku Premium \
  --zone-redundancy enabled \
  --admin-enabled false

# Enable content trust (image signing)
az acr config content-trust update \
  --registry acrtalentiprod \
  --status enabled
```

### 7.2 Configure GitHub Actions Authentication

```bash
# Create service principal for GitHub Actions
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "sp-github-talenti" \
  --role contributor \
  --scopes /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/rg-talenti-prod-aue \
  --sdk-auth)

echo "$SP_OUTPUT"
# Save this JSON as AZURE_CREDENTIALS secret in GitHub

# Grant ACR push permission
SP_ID=$(echo $SP_OUTPUT | jq -r .clientId)
ACR_ID=$(az acr show --name acrtalentiprod --query id -o tsv)

az role assignment create \
  --assignee $SP_ID \
  --role AcrPush \
  --scope $ACR_ID
```

### 7.3 Build and Push Image

```bash
# Build locally
docker build -t talenti-api:latest .

# Tag for ACR
docker tag talenti-api:latest acrtalentiprod.azurecr.io/talenti-api:latest

# Login to ACR
az acr login --name acrtalentiprod

# Push image
docker push acrtalentiprod.azurecr.io/talenti-api:latest

# Or build directly in ACR
az acr build \
  --registry acrtalentiprod \
  --image talenti-api:latest \
  --image talenti-api:$(git rev-parse --short HEAD) \
  --file Dockerfile \
  .
```

---

## 8. Database & Storage Setup

### 8.1 Storage Account Configuration

```bash
# Create storage account
az storage account create \
  --name sttalentiprodaue \
  --resource-group rg-talenti-prod-aue \
  --location australiaeast \
  --sku Standard_ZRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false

# Create containers
az storage container create \
  --name interview-recordings \
  --account-name sttalentiprodaue \
  --auth-mode login

az storage container create \
  --name candidate-documents \
  --account-name sttalentiprodaue \
  --auth-mode login

# Configure lifecycle management
az storage account management-policy create \
  --account-name sttalentiprodaue \
  --policy @storage-lifecycle-policy.json
```

### 8.2 Storage Lifecycle Policy

```json
{
  "rules": [
    {
      "enabled": true,
      "name": "delete-old-recordings",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterModificationGreaterThan": 30
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["interview-recordings/"]
        }
      }
    },
    {
      "enabled": true,
      "name": "archive-old-exports",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "tierToArchive": {
              "daysAfterModificationGreaterThan": 90
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["exports/"]
        }
      }
    }
  ]
}
```

---

## 9. Networking & Security

### 9.1 Network Security Configuration

```bicep
// infra/modules/networking.bicep

param location string
param tags object
param vnetName string = 'vnet-talenti'
param addressPrefix string = '10.0.0.0/16'

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [addressPrefix]
    }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: '10.0.0.0/23'
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Network Security Group
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-container-apps'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPS'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}
```

### 9.2 Private Endpoints

```bash
# Create private endpoint for Key Vault
az network private-endpoint create \
  --name pe-keyvault-talenti \
  --resource-group rg-talenti-prod-aue \
  --vnet-name vnet-talenti \
  --subnet snet-private-endpoints \
  --private-connection-resource-id $(az keyvault show --name kv-talenti-prod-aue --query id -o tsv) \
  --group-id vault \
  --connection-name conn-keyvault

# Create private endpoint for Storage
az network private-endpoint create \
  --name pe-storage-talenti \
  --resource-group rg-talenti-prod-aue \
  --vnet-name vnet-talenti \
  --subnet snet-private-endpoints \
  --private-connection-resource-id $(az storage account show --name sttalentiprodaue --query id -o tsv) \
  --group-id blob \
  --connection-name conn-storage
```

---

## 10. Monitoring & Observability

### 10.1 Application Insights Configuration

```python
# app/monitoring.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

def configure_telemetry(app, connection_string: str):
    """Configure OpenTelemetry with Azure Monitor"""
    
    # Set up trace provider
    provider = TracerProvider()
    
    # Azure Monitor exporter
    azure_exporter = AzureMonitorTraceExporter(
        connection_string=connection_string
    )
    provider.add_span_processor(BatchSpanProcessor(azure_exporter))
    
    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTP clients
    HTTPXClientInstrumentor().instrument()
```

### 10.2 Custom Metrics

```python
# app/metrics.py
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter

def configure_metrics(connection_string: str):
    """Configure custom metrics"""
    
    exporter = AzureMonitorMetricExporter(
        connection_string=connection_string
    )
    
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    
    meter = metrics.get_meter("talenti.api")
    
    # Custom metrics
    interview_counter = meter.create_counter(
        "interviews_completed",
        description="Number of completed interviews"
    )
    
    scoring_histogram = meter.create_histogram(
        "scoring_duration_ms",
        description="Interview scoring duration in milliseconds"
    )
    
    return {
        "interview_counter": interview_counter,
        "scoring_histogram": scoring_histogram
    }
```

### 10.3 Log Analytics Queries

```kusto
// Container App requests
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-api-talenti-prod-aue"
| where Log_s contains "ERROR" or Log_s contains "CRITICAL"
| project TimeGenerated, Log_s, ContainerName_s
| order by TimeGenerated desc
| take 100

// Request latency percentiles
requests
| where cloud_RoleName == "talenti-api"
| summarize 
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99)
  by bin(timestamp, 5m)
| render timechart

// Error rate
requests
| where cloud_RoleName == "talenti-api"
| summarize 
    total = count(),
    errors = countif(success == false)
  by bin(timestamp, 5m)
| extend error_rate = errors * 100.0 / total
| render timechart
```

### 10.4 Alerting Rules

```bash
# Create action group
az monitor action-group create \
  --name ag-talenti-alerts \
  --resource-group rg-talenti-prod-aue \
  --short-name talenti \
  --email-receiver name=ops email=ops@talenti.app

# High error rate alert
az monitor metrics alert create \
  --name "High Error Rate" \
  --resource-group rg-talenti-prod-aue \
  --scopes $(az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query id -o tsv) \
  --condition "avg requests/failed > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action ag-talenti-alerts \
  --severity 2

# High latency alert
az monitor metrics alert create \
  --name "High Latency" \
  --resource-group rg-talenti-prod-aue \
  --scopes $(az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query id -o tsv) \
  --condition "avg requests/duration > 5000" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action ag-talenti-alerts \
  --severity 3
```

---

## 11. Scaling Configuration

### 11.1 Horizontal Pod Autoscaling

```bicep
// In container-app.bicep
scale: {
  minReplicas: 2
  maxReplicas: 10
  rules: [
    // HTTP-based scaling
    {
      name: 'http-scaling'
      http: {
        metadata: {
          concurrentRequests: '100'
        }
      }
    }
    // CPU-based scaling
    {
      name: 'cpu-scaling'
      custom: {
        type: 'cpu'
        metadata: {
          type: 'Utilization'
          value: '70'
        }
      }
    }
    // Memory-based scaling
    {
      name: 'memory-scaling'
      custom: {
        type: 'memory'
        metadata: {
          type: 'Utilization'
          value: '80'
        }
      }
    }
    // Queue-based scaling (for workers)
    {
      name: 'queue-scaling'
      custom: {
        type: 'azure-servicebus'
        metadata: {
          queueName: 'interview-jobs'
          messageCount: '5'
        }
        auth: [
          {
            secretRef: 'servicebus-connection'
            triggerParameter: 'connection'
          }
        ]
      }
    }
  ]
}
```

### 11.2 Load Testing

```bash
# Install Azure Load Testing CLI extension
az extension add --name load

# Create load test
az load test create \
  --name lt-talenti-api \
  --resource-group rg-talenti-prod-aue \
  --location australiaeast

# Run load test
az load test-run create \
  --name run-$(date +%Y%m%d-%H%M%S) \
  --test-id lt-talenti-api \
  --resource-group rg-talenti-prod-aue \
  --load-test-resource lt-talenti-api \
  --test-plan load-test.jmx
```

---

## 12. Disaster Recovery

### 12.1 Backup Strategy

```bash
# Storage account geo-replication
az storage account update \
  --name sttalentiprodaue \
  --sku Standard_RAGRS

# Key Vault soft-delete and purge protection
az keyvault update \
  --name kv-talenti-prod-aue \
  --enable-soft-delete true \
  --enable-purge-protection true

# ACR geo-replication
az acr replication create \
  --registry acrtalentiprod \
  --location southeastasia
```

### 12.2 Recovery Runbook

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

set -euo pipefail

RECOVERY_REGION="southeastasia"
SOURCE_RG="rg-talenti-prod-aue"
RECOVERY_RG="rg-talenti-dr-sea"

echo "=== DISASTER RECOVERY PROCEDURE ==="
echo "Recovery Region: $RECOVERY_REGION"
echo "Started at: $(date -u)"

# 1. Create recovery resource group
echo "Creating recovery resource group..."
az group create \
  --name $RECOVERY_RG \
  --location $RECOVERY_REGION

# 2. Deploy infrastructure to recovery region
echo "Deploying infrastructure..."
az deployment group create \
  --resource-group $RECOVERY_RG \
  --template-file infra/main.bicep \
  --parameters environment=dr location=$RECOVERY_REGION

# 3. Update DNS to point to recovery region
echo "Updating DNS..."
# Add DNS update commands here

# 4. Notify team
echo "Sending notifications..."
# Add notification commands here

echo "=== RECOVERY COMPLETE ==="
echo "Completed at: $(date -u)"
```

### 12.3 RTO/RPO Targets

| Component | RPO | RTO | Strategy |
|-----------|-----|-----|----------|
| API Service | 0 | 5 min | Multi-region Container Apps |
| Database (Supabase) | 24 hrs | 1 hr | Point-in-time recovery |
| Blob Storage | 0 | 15 min | RA-GRS replication |
| Key Vault | 0 | 10 min | Soft-delete + geo-backup |
| Container Registry | 0 | 5 min | Geo-replication |

---

## 13. Troubleshooting Guide

### 13.1 Common Issues

#### Container App Not Starting

```bash
# Check revision status
az containerapp revision list \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --query "[].{name:name, status:properties.runningState, created:properties.createdTime}" \
  --output table

# View container logs
az containerapp logs show \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --follow

# Check system logs
az containerapp logs show \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --type system
```

#### Image Pull Failures

```bash
# Verify ACR connectivity
az acr check-health \
  --name acrtalentiprod \
  --yes

# Check managed identity permissions
az role assignment list \
  --assignee $(az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query "identity.userAssignedIdentities.*.principalId" -o tsv) \
  --scope $(az acr show --name acrtalentiprod --query id -o tsv) \
  --output table
```

#### Secret Access Issues

```bash
# Verify Key Vault access
az keyvault secret list \
  --vault-name kv-talenti-prod-aue \
  --query "[].name" -o table

# Check managed identity Key Vault permissions
az role assignment list \
  --assignee $(az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query "identity.userAssignedIdentities.*.principalId" -o tsv) \
  --scope $(az keyvault show --name kv-talenti-prod-aue --query id -o tsv) \
  --output table
```

### 13.2 Performance Issues

```bash
# Check container metrics
az monitor metrics list \
  --resource $(az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query id -o tsv) \
  --metric "CpuUsage" "MemoryUsage" "Requests" \
  --interval PT1M \
  --output table

# Check scaling history
az containerapp revision list \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --query "[].{name:name, replicas:properties.replicas}" \
  --output table
```

### 13.3 Debug Commands Cheatsheet

```bash
# Quick health check
curl -s https://ca-api-talenti-prod-aue.australiaeast.azurecontainerapps.io/health/ready | jq

# Get current deployment info
az containerapp show \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --query "{fqdn:properties.configuration.ingress.fqdn, latestRevision:properties.latestRevisionName, replicas:properties.template.scale}" \
  --output json | jq

# Stream logs with filter
az containerapp logs show \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --follow \
  --format text \
  | grep -E "(ERROR|CRITICAL|Exception)"

# Execute command in container
az containerapp exec \
  --name ca-api-talenti-prod-aue \
  --resource-group rg-talenti-prod-aue \
  --command "python -c 'import sys; print(sys.version)'"
```

---

## 14. Cost Optimization

### 14.1 Cost Breakdown (Estimated Monthly)

| Resource | SKU | Est. Cost (AUD) |
|----------|-----|-----------------|
| Container Apps (API) | 2-10 replicas | $150-400 |
| Container Apps (Worker) | 1-5 replicas | $50-150 |
| Container Registry | Premium | $75 |
| Key Vault | Standard | $5 |
| Storage Account | Standard ZRS | $25 |
| Log Analytics | Per GB ingested | $50-100 |
| Application Insights | Per GB ingested | $30-50 |
| Azure OpenAI | Per 1K tokens | $100-500 |
| Azure Speech | Per audio hour | $50-200 |
| **Total** | | **$535-1,480** |

### 14.2 Cost Saving Recommendations

```bash
# 1. Use Consumption tier for non-prod
az containerapp env update \
  --name cae-talenti-dev-aue \
  --resource-group rg-talenti-dev-aue \
  --workload-profile-type Consumption

# 2. Enable auto-shutdown for dev environment
az containerapp update \
  --name ca-api-talenti-dev-aue \
  --resource-group rg-talenti-dev-aue \
  --min-replicas 0

# 3. Configure log retention
az monitor log-analytics workspace update \
  --resource-group rg-talenti-dev-aue \
  --workspace-name law-talenti-dev-aue \
  --retention-time 30

# 4. Use reserved instances for predictable workloads
# Configure in Azure Portal > Reservations
```

### 14.3 Cost Monitoring

```bash
# View current month costs
az consumption usage list \
  --subscription $AZURE_SUBSCRIPTION_ID \
  --start-date $(date -d "$(date +%Y-%m-01)" +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?contains(instanceName, 'talenti')].{name:instanceName, cost:pretaxCost}" \
  --output table

# Set up budget alert
az consumption budget create \
  --budget-name budget-talenti-monthly \
  --amount 2000 \
  --category Cost \
  --time-grain Monthly \
  --start-date $(date +%Y-%m-01) \
  --end-date 2025-12-31 \
  --resource-group rg-talenti-prod-aue
```

---

## Appendix A: Quick Reference Commands

```bash
# ===== DEPLOYMENT =====
# Deploy to dev
az deployment group create -g rg-talenti-dev-aue -f infra/main.bicep -p @infra/parameters/dev.bicepparam

# Deploy to prod
az deployment group create -g rg-talenti-prod-aue -f infra/main.bicep -p @infra/parameters/prod.bicepparam

# ===== CONTAINER MANAGEMENT =====
# Update container image
az containerapp update -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --image acrtalentiprod.azurecr.io/talenti-api:v1.2.3

# Scale manually
az containerapp update -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --min-replicas 5 --max-replicas 20

# Restart container
az containerapp revision restart -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --revision <revision-name>

# ===== SECRETS =====
# Update secret
az keyvault secret set --vault-name kv-talenti-prod-aue --name azure-openai-key --value "<new-value>"

# ===== LOGS =====
# Stream logs
az containerapp logs show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --follow

# Query App Insights
az monitor app-insights query --app appi-talenti-prod-aue -g rg-talenti-prod-aue --analytics-query "requests | take 10"

# ===== TROUBLESHOOTING =====
# Check health
curl -s https://<fqdn>/health/ready | jq

# List revisions
az containerapp revision list -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue -o table

# Get container app URL
az containerapp show -n ca-api-talenti-prod-aue -g rg-talenti-prod-aue --query "properties.configuration.ingress.fqdn" -o tsv
```

---

## Appendix B: File Checksums

```bash
# Generate checksums for infrastructure files
find infra/ -type f -name "*.bicep" -exec sha256sum {} \;

# Verify before deployment
sha256sum -c infra-checksums.txt
```

---

*Last Updated: January 2026*
*Document Version: 1.0.0*
