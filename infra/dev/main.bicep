targetScope = 'resourceGroup'

@description('Primary location for dev resources.')
param location string = resourceGroup().location
@description('Region for the DEV Static Web App resource.')
param staticWebAppLocation string = 'eastasia'

@secure()
param postgresAdminPassword string
param postgresAdminUser string = 'talentiadmin'
param alertEmailAddress string

module platform '../modules/platform.bicep' = {
  name: 'talenti-dev-platform'
  params: {
    location: location
    environmentName: 'dev'
    logAnalyticsName: 'log-talenti-dev-aue'
    appInsightsName: 'appi-talenti-dev-aue'
    containerEnvName: 'cae-talenti-dev-aue'
    acrName: 'acrtalentidev'
    keyVaultName: 'kv-talenti-dev-aue'
    storageAccountName: 'sttalentidevaue'
    postgresServerName: 'psql-talenti-dev-aue'
    backendDbName: 'talenti_backend_dev'
    staticWebAppName: 'swa-talenti-dev-aue'
    frontendHostingMode: 'staticwebapp'
    staticWebAppLocation: staticWebAppLocation
    backendAppName: 'ca-backend-dev'
    backendWorkerAppName: 'ca-backend-worker-dev'
    model1AppName: 'ca-model1-dev'
    model2AppName: 'ca-model2-dev'
    acsWorkerAppName: 'ca-acs-worker-dev'
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
