targetScope = 'resourceGroup'

@description('Primary location for dev resources.')
param location string = resourceGroup().location

param logAnalyticsName string = 'log-talenti-dev-aue'
param containerEnvName string = 'cae-talenti-dev-aue'
param acrName string = 'acrtalentidev'
param keyVaultName string = 'kv-talenti-dev-aue'
param storageAccountName string = 'sttalentidevaue'
param postgresServerName string = 'psql-talenti-dev-aue'
param backendDbName string = 'talenti_backend_dev'

param backendAppName string = 'ca-backend-dev'
param model1AppName string = 'ca-model1-dev'
param model2AppName string = 'ca-model2-dev'
param acsWorkerAppName string = 'ca-acs-worker-dev'

param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param model1Image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param model2Image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param acsWorkerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@secure()
param postgresAdminPassword string
param postgresAdminUser string = 'talentiadmin'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-talenti-dev-aue'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enableRbacAuthorization: true
    enabledForTemplateDeployment: true
    softDeleteRetentionInDays: 90
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource recordingsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/recordings'
  properties: {
    publicAccess: 'None'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource backendDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  name: '${postgres.name}/${backendDbName}'
}

resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: backendAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource model1App 'Microsoft.App/containerApps@2023-05-01' = {
  name: model1AppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8001
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'model1'
          image: model1Image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

resource model2App 'Microsoft.App/containerApps@2023-05-01' = {
  name: model2AppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8002
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'model2'
          image: model2Image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

resource acsWorkerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: acsWorkerAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'acs-worker'
          image: acsWorkerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output keyVaultId string = keyVault.id
output acrLoginServer string = '${acr.name}.azurecr.io'
