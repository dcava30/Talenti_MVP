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
@allowed([
  'staticwebapp'
  'storage-frontdoor'
  'storage-appgateway'
])
param frontendHostingMode string = 'staticwebapp'
param staticWebAppLocation string = location
param frontDoorProfileName string = ''
param frontDoorEndpointName string = ''
param frontDoorAllowedCidrs array = []
param applicationGatewayName string = ''
param applicationGatewayPublicIpName string = ''
param applicationGatewayFrontendHostName string = ''
@secure()
param applicationGatewaySslCertificateData string = ''
@secure()
param applicationGatewaySslCertificatePassword string = ''
param applicationGatewayAllowedCidrs array = []

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
param alertEmailAddress string = ''
param deployBackendWorker bool = true
param deployModelServices bool = true
param deployAcsWorker bool = true
param enableAlerts bool = true
param enableSyntheticTests bool = true
param backendMinReplicas int = 1
param backendMaxReplicas int = 2
param backendAllowedCidrs array = []

var monitoringTag = {
  environment: environmentName
  managedBy: 'bicep'
  workload: 'talenti'
}

var frontendUsesStaticWebApp = frontendHostingMode == 'staticwebapp'
var frontendUsesFrontDoor = frontendHostingMode == 'storage-frontdoor'
var frontendUsesAppGateway = frontendHostingMode == 'storage-appgateway'
var resolvedFrontDoorProfileName = empty(frontDoorProfileName) ? 'fdp-talenti-${environmentName}' : frontDoorProfileName
var resolvedFrontDoorEndpointName = empty(frontDoorEndpointName) ? 'afd-talenti-${environmentName}' : frontDoorEndpointName
var resolvedApplicationGatewayName = empty(applicationGatewayName) ? 'agw-talenti-${environmentName}' : applicationGatewayName
var resolvedApplicationGatewayPublicIpName = empty(applicationGatewayPublicIpName) ? 'pip-talenti-${environmentName}-agw' : applicationGatewayPublicIpName
var applicationGatewayVnetName = 'vnet-talenti-${environmentName}-edge'
var applicationGatewaySubnetName = 'snet-appgateway'
var applicationGatewayWafPolicyName = 'waf-agw-talenti-${environmentName}'
var applicationGatewayProbeName = 'probe-frontend-${environmentName}'
var applicationGatewayRedirectName = 'redirect-https-${environmentName}'
var frontDoorWafPolicyName = 'waf-talenti-${environmentName}'
var frontDoorSecurityPolicyName = 'security-talenti-${environmentName}'
var backendAvailabilityTestName = 'wt-talenti-backend-${environmentName}'
var frontendAvailabilityTestName = 'wt-talenti-frontend-${environmentName}'
var backendAvailabilityTestId = guid(resourceGroup().id, backendAvailabilityTestName)
var frontendAvailabilityTestId = guid(resourceGroup().id, frontendAvailabilityTestName)
var backendHealthUrl = 'https://${backendApp.properties.configuration.ingress.fqdn}/health'
var storageStaticWebsiteHost = replace(replace(storage.properties.primaryEndpoints.web, 'https://', ''), '/', '')
var frontendPublicUrl = frontendUsesStaticWebApp
  ? 'https://${staticWebApp!.properties.defaultHostname}'
  : frontendUsesFrontDoor
      ? 'https://${frontDoorEndpoint!.properties.hostName}'
      : 'https://${applicationGatewayFrontendHostName}'
var backendIpSecurityRestrictions = [for (cidr, idx) in backendAllowedCidrs: {
  name: 'allow-${idx + 1}'
  description: 'Allow proxied ingress CIDR ${cidr}'
  ipAddressRange: cidr
  action: 'Allow'
}]
var syntheticLocations = [
  {
    Id: 'us-tx-sn1-azr'
  }
]
var monitoredApps = concat(
  [
    {
      name: backendAppName
      resourceId: backendApp.id
    }
  ],
  deployBackendWorker ? [
    {
      name: backendWorkerAppName
      resourceId: backendWorkerApp.id
    }
  ] : [],
  deployModelServices ? [
    {
      name: model1AppName
      resourceId: model1App.id
    }
    {
      name: model2AppName
      resourceId: model2App.id
    }
  ] : [],
  deployAcsWorker ? [
    {
      name: acsWorkerAppName
      resourceId: acsWorkerApp.id
    }
  ] : []
)

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

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = if (enableAlerts) {
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
  parent: postgres
  name: backendDbName
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
        ipSecurityRestrictions: backendIpSecurityRestrictions
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
        minReplicas: backendMinReplicas
        maxReplicas: backendMaxReplicas
      }
    }
  }
}

resource backendWorkerApp 'Microsoft.App/containerApps@2023-05-01' = if (deployBackendWorker) {
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

resource model1App 'Microsoft.App/containerApps@2023-05-01' = if (deployModelServices) {
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

resource model2App 'Microsoft.App/containerApps@2023-05-01' = if (deployModelServices) {
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

resource acsWorkerApp 'Microsoft.App/containerApps@2023-05-01' = if (deployAcsWorker) {
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

resource frontDoorProfile 'Microsoft.Cdn/profiles@2021-06-01' = if (frontendUsesFrontDoor) {
  name: resolvedFrontDoorProfileName
  location: 'global'
  tags: monitoringTag
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
  properties: {
    originResponseTimeoutSeconds: 120
  }
}

resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2021-06-01' = if (frontendUsesFrontDoor) {
  parent: frontDoorProfile
  name: resolvedFrontDoorEndpointName
  location: 'global'
  properties: {
    enabledState: 'Enabled'
  }
}

resource frontDoorOriginGroup 'Microsoft.Cdn/profiles/originGroups@2021-06-01' = if (frontendUsesFrontDoor) {
  parent: frontDoorProfile
  name: 'og-frontend-${environmentName}'
  properties: {
    loadBalancingSettings: {
      additionalLatencyInMilliseconds: 0
      sampleSize: 4
      successfulSamplesRequired: 3
    }
    healthProbeSettings: {
      probeIntervalInSeconds: 120
      probePath: '/'
      probeProtocol: 'Https'
      probeRequestType: 'GET'
    }
    sessionAffinityState: 'Disabled'
    trafficRestorationTimeToHealedOrNewEndpointsInMinutes: 10
  }
}

resource frontDoorOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2021-06-01' = if (frontendUsesFrontDoor) {
  parent: frontDoorOriginGroup
  name: 'origin-frontend-${environmentName}'
  properties: {
    enabledState: 'Enabled'
    enforceCertificateNameCheck: true
    hostName: storageStaticWebsiteHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: storageStaticWebsiteHost
    priority: 1
    weight: 1000
  }
}

resource frontDoorRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2021-06-01' = if (frontendUsesFrontDoor) {
  parent: frontDoorEndpoint
  name: 'route-frontend-${environmentName}'
  properties: {
    enabledState: 'Enabled'
    forwardingProtocol: 'MatchRequest'
    httpsRedirect: 'Enabled'
    linkToDefaultDomain: 'Enabled'
    originGroup: {
      id: frontDoorOriginGroup.id
    }
    patternsToMatch: [
      '/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
  }
}

resource frontDoorWafPolicy 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2024-02-01' = if (frontendUsesFrontDoor) {
  name: frontDoorWafPolicyName
  location: 'global'
  tags: monitoringTag
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
  properties: {
    customRules: {
      rules: length(frontDoorAllowedCidrs) > 0 ? [
        {
          action: 'Block'
          enabledState: 'Enabled'
          matchConditions: [
            {
              matchValue: frontDoorAllowedCidrs
              matchVariable: 'RemoteAddr'
              negateCondition: true
              operator: 'IPMatch'
            }
          ]
          name: 'AllowApprovedCidrsOnly'
          priority: 1
          ruleType: 'MatchRule'
        }
      ] : []
    }
    managedRules: {
      managedRuleSets: []
    }
    policySettings: {
      enabledState: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: 'Enabled'
    }
  }
}

resource frontDoorSecurityPolicy 'Microsoft.Cdn/profiles/securityPolicies@2024-02-01' = if (frontendUsesFrontDoor) {
  parent: frontDoorProfile
  name: frontDoorSecurityPolicyName
  properties: {
    parameters: {
      type: 'WebApplicationFirewall'
      associations: [
        {
          domains: [
            {
              id: frontDoorEndpoint.id
            }
          ]
          patternsToMatch: [
            '/*'
          ]
        }
      ]
      wafPolicy: {
        id: frontDoorWafPolicy.id
      }
    }
  }
}

resource applicationGatewayVnet 'Microsoft.Network/virtualNetworks@2023-09-01' = if (frontendUsesAppGateway) {
  name: applicationGatewayVnetName
  location: location
  tags: monitoringTag
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/24'
      ]
    }
  }
}

resource applicationGatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2023-09-01' = if (frontendUsesAppGateway) {
  parent: applicationGatewayVnet
  name: applicationGatewaySubnetName
  properties: {
    addressPrefix: '10.42.0.0/27'
  }
}

resource applicationGatewayPublicIp 'Microsoft.Network/publicIPAddresses@2023-09-01' = if (frontendUsesAppGateway) {
  name: resolvedApplicationGatewayPublicIpName
  location: location
  tags: monitoringTag
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource applicationGatewayWafPolicy 'Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies@2023-09-01' = if (frontendUsesAppGateway) {
  name: applicationGatewayWafPolicyName
  location: location
  tags: monitoringTag
  properties: {
    customRules: length(applicationGatewayAllowedCidrs) > 0 ? [
      {
        name: 'AllowApprovedCidrsOnly'
        priority: 1
        ruleType: 'MatchRule'
        action: 'Block'
        state: 'Enabled'
        matchConditions: [
          {
            matchVariables: [
              {
                variableName: 'RemoteAddr'
              }
            ]
            operator: 'IPMatch'
            negationConditon: true
            matchValues: applicationGatewayAllowedCidrs
          }
        ]
      }
    ] : []
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'OWASP'
          ruleSetVersion: '3.2'
        }
      ]
    }
    policySettings: {
      state: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: true
      maxRequestBodySizeInKb: 128
      fileUploadLimitInMb: 100
    }
  }
}

resource applicationGateway 'Microsoft.Network/applicationGateways@2023-09-01' = if (frontendUsesAppGateway) {
  name: resolvedApplicationGatewayName
  location: location
  tags: monitoringTag
  properties: {
    sku: {
      name: 'WAF_v2'
      tier: 'WAF_v2'
      capacity: 1
    }
    gatewayIPConfigurations: [
      {
        name: 'gateway-ip-config'
        properties: {
          subnet: {
            id: applicationGatewaySubnet.id
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'frontend-ip'
        properties: {
          publicIPAddress: {
            id: applicationGatewayPublicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port-80'
        properties: {
          port: 80
        }
      }
      {
        name: 'port-443'
        properties: {
          port: 443
        }
      }
    ]
    sslCertificates: [
      {
        name: 'frontend-cert'
        properties: {
          data: applicationGatewaySslCertificateData
          password: applicationGatewaySslCertificatePassword
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'frontend-storage-pool'
        properties: {
          backendAddresses: [
            {
              fqdn: storageStaticWebsiteHost
            }
          ]
        }
      }
    ]
    probes: [
      {
        name: applicationGatewayProbeName
        properties: {
          protocol: 'Https'
          path: '/'
          interval: 120
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          match: {
            statusCodes: [
              '200-399'
            ]
          }
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: 'frontend-storage-https'
        properties: {
          port: 443
          protocol: 'Https'
          cookieBasedAffinity: 'Disabled'
          requestTimeout: 120
          pickHostNameFromBackendAddress: true
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', resolvedApplicationGatewayName, applicationGatewayProbeName)
          }
        }
      }
    ]
    httpListeners: [
      {
        name: 'listener-http'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', resolvedApplicationGatewayName, 'frontend-ip')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', resolvedApplicationGatewayName, 'port-80')
          }
          protocol: 'Http'
          hostName: applicationGatewayFrontendHostName
        }
      }
      {
        name: 'listener-https'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', resolvedApplicationGatewayName, 'frontend-ip')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', resolvedApplicationGatewayName, 'port-443')
          }
          protocol: 'Https'
          hostName: applicationGatewayFrontendHostName
          sslCertificate: {
            id: resourceId('Microsoft.Network/applicationGateways/sslCertificates', resolvedApplicationGatewayName, 'frontend-cert')
          }
        }
      }
    ]
    redirectConfigurations: [
      {
        name: applicationGatewayRedirectName
        properties: {
          redirectType: 'Permanent'
          targetListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', resolvedApplicationGatewayName, 'listener-https')
          }
          includePath: true
          includeQueryString: true
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'rule-http-redirect'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', resolvedApplicationGatewayName, 'listener-http')
          }
          redirectConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/redirectConfigurations', resolvedApplicationGatewayName, applicationGatewayRedirectName)
          }
        }
      }
      {
        name: 'rule-frontend-https'
        properties: {
          ruleType: 'Basic'
          priority: 200
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', resolvedApplicationGatewayName, 'listener-https')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', resolvedApplicationGatewayName, 'frontend-storage-pool')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', resolvedApplicationGatewayName, 'frontend-storage-https')
          }
        }
      }
    ]
    enableHttp2: true
    firewallPolicy: {
      id: applicationGatewayWafPolicy.id
    }
  }
}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = if (frontendUsesStaticWebApp) {
  name: staticWebAppName
  location: staticWebAppLocation
  tags: monitoringTag
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {}
}

resource backendAvailabilityWebTest 'Microsoft.Insights/webtests@2022-06-15' = if (enableSyntheticTests) {
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

resource frontendAvailabilityWebTestStatic 'Microsoft.Insights/webtests@2022-06-15' = if (enableSyntheticTests && (frontendUsesStaticWebApp || frontendUsesFrontDoor || frontendUsesAppGateway)) {
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
      WebTest: '<WebTest Name="${frontendAvailabilityTestName}" Id="${frontendAvailabilityTestId}" Enabled="True" Timeout="30" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Items><Request Method="GET" Guid="${frontendAvailabilityTestId}" Version="1.1" Url="${frontendPublicUrl}" ThinkTime="0" Timeout="30" ParseDependentRequests="False" FollowRedirects="True" RecordResult="True" Cache="False" ExpectedHttpStatusCode="200" IgnoreHttpStatusCode="False" /></Items></WebTest>'
    }
  }
}

resource backendAvailabilityAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = if (enableAlerts && enableSyntheticTests) {
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

resource frontendAvailabilityAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = if (enableAlerts && enableSyntheticTests) {
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

resource jobQueueBacklogAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = if (enableAlerts && deployBackendWorker) {
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

resource jobQueueAgeAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = if (enableAlerts && deployBackendWorker) {
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

resource backend5xxAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = if (enableAlerts) {
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

resource backendLatencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = if (enableAlerts) {
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

resource restartAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for app in monitoredApps: if (enableAlerts) {
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
output frontendUrl string = frontendPublicUrl
output keyVaultId string = keyVault.id
output acrLoginServer string = '${acr.name}.azurecr.io'
output applicationInsightsId string = appInsights.id
output logAnalyticsWorkspaceId string = logAnalytics.id
