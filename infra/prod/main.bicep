targetScope = 'resourceGroup'

@description('Primary location for production resources.')
param location string = resourceGroup().location

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
    frontendHostingMode: 'storage-frontdoor'
    frontDoorProfileName: 'fdp-talenti-prod-aue'
    frontDoorEndpointName: 'afd-talenti-prod-aue'
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
