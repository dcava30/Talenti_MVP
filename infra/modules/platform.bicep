targetScope = 'resourceGroup'

param location string = resourceGroup().location
param environmentName string

param logAnalyticsName string
param appInsightsName string
param containerEnvName string
param acrName string
param keyVaultName string
param storageAccountName string
param postgresServerName string
param backendDbName string
param staticWebAppName string

param backendAppName string
param backendWorkerAppName string
param model1AppName string
param model2AppName string
param acsWorkerAppName string

param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param backendWorkerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param model1Image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param model2Image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param acsWorkerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@secure()
param postgresAdminPassword string
param postgresAdminUser string = 'talentiadmin'
param alertEmailAddress string

var monitoringTag = {
  environment: environmentName
  managedBy: 'bicep'
  workload: 'talenti'
}

var backendAvailabilityTestName = 'wt-talenti-backend-${environmentName}'
var frontendAvailabilityTestName = 'wt-talenti-frontend-${environmentName}'
var backendAvailabilityTestId = guid(resourceGroup().id, backendAvailabilityTestName)
var frontendAvailabilityTestId = guid(resourceGroup().id, frontendAvailabilityTestName)
var backendHealthUrl = 'https://${backendApp.properties.configuration.ingress.fqdn}/health'
var frontendUrl = 'https://${staticWebApp.properties.defaultHostname}'
var syntheticLocations = [
  {
    Id: 'us-tx-sn1-azr'
  }
]
var monitoredApps = [
  {
    name: backendAppName
    resourceId: backendApp.id
  }
  {
    name: backendWorkerAppName
    resourceId: backendWorkerApp.id
  }
  {
    name: model1AppName
    resourceId: model1App.id
  }
  {
    name: model2AppName
    resourceId: model2App.id
  }
  {
    name: acsWorkerAppName
    resourceId: acsWorkerApp.id
  }
]

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: monitoringTag
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: monitoringTag
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-talenti-${environmentName}'
  location: 'global'
  tags: monitoringTag
  properties: {
    enabled: true
    groupShortName: 'tal${take(environmentName, 9)}'
    emailReceivers: [
      {
        name: 'platform-email'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: monitoringTag
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
  tags: monitoringTag
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
  tags: monitoringTag
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
  tags: monitoringTag
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
  tags: monitoringTag
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
  tags: monitoringTag
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
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource backendWorkerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: backendWorkerAppName
  location: location
  tags: monitoringTag
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
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
          name: 'backend-worker'
          image: backendWorkerImage
          command: [
            'python'
            '-m'
            'app.worker_main'
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource model1App 'Microsoft.App/containerApps@2023-05-01' = {
  name: model1AppName
  location: location
  tags: monitoringTag
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
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource model2App 'Microsoft.App/containerApps@2023-05-01' = {
  name: model2AppName
  location: location
  tags: monitoringTag
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
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8002
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8002
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource acsWorkerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: acsWorkerAppName
  location: location
  tags: monitoringTag
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
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/live'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: staticWebAppName
  location: location
  tags: monitoringTag
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {}
}

resource backendAvailabilityWebTest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: backendAvailabilityTestName
  location: location
  kind: 'ping'
  tags: union(monitoringTag, {
    'hidden-link:${appInsights.id}': 'Resource'
  })
  properties: {
    SyntheticMonitorId: backendAvailabilityTestName
    Name: backendAvailabilityTestName
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'ping'
    RetryEnabled: true
    Locations: syntheticLocations
    Configuration: {
      WebTest: '<WebTest Name="${backendAvailabilityTestName}" Id="${backendAvailabilityTestId}" Enabled="True" Timeout="30" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Items><Request Method="GET" Guid="${backendAvailabilityTestId}" Version="1.1" Url="${backendHealthUrl}" ThinkTime="0" Timeout="30" ParseDependentRequests="False" FollowRedirects="True" RecordResult="True" Cache="False" ExpectedHttpStatusCode="200" IgnoreHttpStatusCode="False" /></Items></WebTest>'
    }
  }
}

resource frontendAvailabilityWebTest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: frontendAvailabilityTestName
  location: location
  kind: 'ping'
  tags: union(monitoringTag, {
    'hidden-link:${appInsights.id}': 'Resource'
  })
  properties: {
    SyntheticMonitorId: frontendAvailabilityTestName
    Name: frontendAvailabilityTestName
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'ping'
    RetryEnabled: true
    Locations: syntheticLocations
    Configuration: {
      WebTest: '<WebTest Name="${frontendAvailabilityTestName}" Id="${frontendAvailabilityTestId}" Enabled="True" Timeout="30" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Items><Request Method="GET" Guid="${frontendAvailabilityTestId}" Version="1.1" Url="${frontendUrl}" ThinkTime="0" Timeout="30" ParseDependentRequests="False" FollowRedirects="True" RecordResult="True" Cache="False" ExpectedHttpStatusCode="200" IgnoreHttpStatusCode="False" /></Items></WebTest>'
    }
  }
}

resource backendAvailabilityAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-backend-availability-${environmentName}'
  location: location
  tags: monitoringTag
  properties: {
    description: 'Backend health synthetic check failed.'
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      logAnalytics.id
    ]
    severity: 1
    criteria: {
      allOf: [
        {
          query: 'availabilityResults | where name == "${backendAvailabilityTestName}" and success == false | summarize failureCount=count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'failureCount'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
    skipQueryValidation: true
  }
}

resource frontendAvailabilityAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-frontend-availability-${environmentName}'
  location: location
  tags: monitoringTag
  properties: {
    description: 'Frontend synthetic check failed.'
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      logAnalytics.id
    ]
    severity: 1
    criteria: {
      allOf: [
        {
          query: 'availabilityResults | where name == "${frontendAvailabilityTestName}" and success == false | summarize failureCount=count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'failureCount'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
    skipQueryValidation: true
  }
}

resource jobQueueBacklogAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-job-queue-backlog-${environmentName}'
  location: location
  tags: monitoringTag
  properties: {
    description: 'Background job queue backlog is above threshold.'
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    scopes: [
      logAnalytics.id
    ]
    severity: 2
    criteria: {
      allOf: [
        {
          query: 'ContainerAppConsoleLogs_CL | where ContainerAppName_s == "${backendWorkerAppName}" | extend payload = parse_json(Log_s) | where tostring(payload.event) == "job_queue_metrics" | summarize pending_jobs=max(todouble(payload.pending_jobs))'
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'pending_jobs'
          operator: 'GreaterThan'
          threshold: 25
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
    skipQueryValidation: true
  }
}

resource jobQueueAgeAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-job-queue-age-${environmentName}'
  location: location
  tags: monitoringTag
  properties: {
    description: 'Background job queue age is above threshold.'
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    scopes: [
      logAnalytics.id
    ]
    severity: 2
    criteria: {
      allOf: [
        {
          query: 'ContainerAppConsoleLogs_CL | where ContainerAppName_s == "${backendWorkerAppName}" | extend payload = parse_json(Log_s) | where tostring(payload.event) == "job_queue_metrics" | summarize oldest_pending_job_age_seconds=max(todouble(payload.oldest_pending_job_age_seconds))'
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'oldest_pending_job_age_seconds'
          operator: 'GreaterThan'
          threshold: 900
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
    skipQueryValidation: true
  }
}

resource backend5xxAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-backend-5xx-${environmentName}'
  location: 'global'
  tags: monitoringTag
  properties: {
    description: 'Backend 5xx responses exceeded the threshold.'
    severity: 2
    enabled: true
    scopes: [
      backendApp.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    autoMitigate: true
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'backend5xx'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'Requests'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Total'
          dimensions: [
            {
              name: 'statusCodeCategory'
              operator: 'Include'
              values: [
                '5xx'
              ]
            }
          ]
          skipMetricValidation: true
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource backendLatencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-backend-latency-${environmentName}'
  location: 'global'
  tags: monitoringTag
  properties: {
    description: 'Backend latency exceeded the threshold.'
    severity: 2
    enabled: true
    scopes: [
      backendApp.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    autoMitigate: true
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'backendLatency'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'ResponseTime'
          operator: 'GreaterThan'
          threshold: 2000
          timeAggregation: 'Average'
          skipMetricValidation: true
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource restartAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for app in monitoredApps: {
  name: 'alert-${app.name}-restarts'
  location: 'global'
  tags: monitoringTag
  properties: {
    description: 'Container restarts exceeded the threshold.'
    severity: 2
    enabled: true
    scopes: [
      app.resourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    autoMitigate: true
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'restartCount'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'RestartCount'
          operator: 'GreaterThan'
          threshold: 3
          timeAggregation: 'Total'
          skipMetricValidation: true
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}]

output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = frontendUrl
output keyVaultId string = keyVault.id
output acrLoginServer string = '${acr.name}.azurecr.io'
output applicationInsightsId string = appInsights.id
output logAnalyticsWorkspaceId string = logAnalytics.id
