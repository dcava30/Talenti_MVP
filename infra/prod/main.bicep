targetScope = 'resourceGroup'

@description('Primary location for production resources.')
param location string = resourceGroup().location
@description('Frontend edge mode for production. Use storage-appgateway for the lower-cost regional path, or storage-frontdoor for the future-state global edge.')
@allowed([
  'storage-frontdoor'
  'storage-appgateway'
])
param frontendHostingMode string = 'storage-frontdoor'
@description('Allowlisted CIDR ranges for the production frontend WAF policy.')
param frontendAllowedCidrs array = []
@description('Application Gateway name to use when frontendHostingMode is storage-appgateway.')
param applicationGatewayName string = 'agw-talenti-prod-aue'
@description('Application Gateway public IP resource name to use when frontendHostingMode is storage-appgateway.')
param applicationGatewayPublicIpName string = 'pip-talenti-prod-aue-agw'
@description('Public frontend hostname served by the Application Gateway listener when frontendHostingMode is storage-appgateway.')
param applicationGatewayFrontendHostName string = ''

@secure()
param applicationGatewaySslCertificateData string = ''
@secure()
param applicationGatewaySslCertificatePassword string = ''

@secure()
param postgresAdminPassword string
param postgresAdminUser string = 'talentiadmin'
param alertEmailAddress string

module platform '../modules/platform.bicep' = {
  name: 'talenti-prod-platform'
  params: {
    location: location
    environmentName: 'prod'
    logAnalyticsName: 'log-talenti-prod-aue'
    appInsightsName: 'appi-talenti-prod-aue'
    containerEnvName: 'cae-talenti-prod-aue'
    acrName: 'acrtalentiprod'
    keyVaultName: 'kv-talenti-prod-aue'
    storageAccountName: 'sttalentiprodaue'
    postgresServerName: 'psql-talenti-prod-aue'
    backendDbName: 'talenti_backend_prod'
    staticWebAppName: 'swa-talenti-prod-aue'
    frontendHostingMode: frontendHostingMode
    frontDoorProfileName: 'fdp-talenti-prod-aue'
    frontDoorEndpointName: 'afd-talenti-prod-aue'
    frontDoorAllowedCidrs: frontendAllowedCidrs
    applicationGatewayName: applicationGatewayName
    applicationGatewayPublicIpName: applicationGatewayPublicIpName
    applicationGatewayFrontendHostName: applicationGatewayFrontendHostName
    applicationGatewaySslCertificateData: applicationGatewaySslCertificateData
    applicationGatewaySslCertificatePassword: applicationGatewaySslCertificatePassword
    applicationGatewayAllowedCidrs: frontendAllowedCidrs
    backendAppName: 'ca-backend-prod'
    backendWorkerAppName: 'ca-backend-worker-prod'
    model1AppName: 'ca-model1-prod'
    model2AppName: 'ca-model2-prod'
    acsWorkerAppName: 'ca-acs-worker-prod'
    postgresAdminPassword: postgresAdminPassword
    postgresAdminUser: postgresAdminUser
    alertEmailAddress: alertEmailAddress
  }
}

output backendUrl string = platform.outputs.backendUrl
output frontendUrl string = platform.outputs.frontendUrl
output keyVaultId string = platform.outputs.keyVaultId
output acrLoginServer string = platform.outputs.acrLoginServer
output applicationInsightsId string = platform.outputs.applicationInsightsId
output logAnalyticsWorkspaceId string = platform.outputs.logAnalyticsWorkspaceId
