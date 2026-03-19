targetScope = 'resourceGroup'

@description('Primary location for UAT resources.')
param location string = resourceGroup().location
@description('Allowlisted CIDR ranges for the UAT Front Door WAF policy.')
param frontDoorAllowedCidrs array = []

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
    frontendHostingMode: 'storage-frontdoor'
    frontDoorProfileName: 'fdp-talenti-uat-aue'
    frontDoorEndpointName: 'afd-talenti-uat-aue'
    frontDoorAllowedCidrs: frontDoorAllowedCidrs
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
