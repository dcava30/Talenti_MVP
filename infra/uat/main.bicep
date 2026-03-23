targetScope = 'resourceGroup'

@description('Primary location for UAT resources.')
param location string = resourceGroup().location
@description('Frontend edge mode for UAT. Use storage-appgateway for the lower-cost regional path, or storage-frontdoor for the future-state global edge.')
@allowed([
  'storage-frontdoor'
  'storage-appgateway'
])
param frontendHostingMode string = 'storage-frontdoor'
@description('Allowlisted CIDR ranges for the UAT frontend WAF policy.')
param frontendAllowedCidrs array = []
@description('Application Gateway name to use when frontendHostingMode is storage-appgateway.')
param applicationGatewayName string = 'agw-talenti-uat-aue'
@description('Application Gateway public IP resource name to use when frontendHostingMode is storage-appgateway.')
param applicationGatewayPublicIpName string = 'pip-talenti-uat-aue-agw'
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
  name: 'talenti-uat-platform'
  params: {
    location: location
    environmentName: 'uat'
    logAnalyticsName: 'log-talenti-uat-aue'
    appInsightsName: 'appi-talenti-uat-aue'
    containerEnvName: 'cae-talenti-uat-aue'
    acrName: 'acrtalentiuat'
    keyVaultName: 'kv-talenti-uat-aue'
    storageAccountName: 'sttalentiuataue'
    postgresServerName: 'psql-talenti-uat-aue'
    backendDbName: 'talenti_backend_uat'
    staticWebAppName: 'swa-talenti-uat-aue'
    frontendHostingMode: frontendHostingMode
    frontDoorProfileName: 'fdp-talenti-uat-aue'
    frontDoorEndpointName: 'afd-talenti-uat-aue'
    frontDoorAllowedCidrs: frontendAllowedCidrs
    applicationGatewayName: applicationGatewayName
    applicationGatewayPublicIpName: applicationGatewayPublicIpName
    applicationGatewayFrontendHostName: applicationGatewayFrontendHostName
    applicationGatewaySslCertificateData: applicationGatewaySslCertificateData
    applicationGatewaySslCertificatePassword: applicationGatewaySslCertificatePassword
    applicationGatewayAllowedCidrs: frontendAllowedCidrs
    backendAppName: 'ca-backend-uat'
    backendWorkerAppName: 'ca-backend-worker-uat'
    model1AppName: 'ca-model1-uat'
    model2AppName: 'ca-model2-uat'
    acsWorkerAppName: 'ca-acs-worker-uat'
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
