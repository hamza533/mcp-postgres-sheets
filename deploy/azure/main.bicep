// mcp-postgres-sheets — Azure production profile (remote mode).
//
//   Container Apps (stateless, scales out)  ─►  client's PostgreSQL (private network)
//        │  user-assigned managed identity  ─►  Key Vault secrets (no secrets in app settings)
//        │  stdout JSON logs + audit lines  ─►  Log Analytics / Application Insights
//        └  bearer tokens validated against Microsoft Entra ID
//
// Validated in CI (`az bicep build` + `az bicep lint`); deployed by .github/workflows/deploy-azure.yml,
// which is disabled by default. See README → Production deployment.

targetScope = 'resourceGroup'

@description('Short name used to derive resource names, e.g. "mcpps".')
@minLength(3)
@maxLength(12)
param prefix string = 'mcpps'

@description('Azure region. Defaults to the resource group\'s region.')
param location string = resourceGroup().location

@description('Container image, pinned to a version, e.g. ghcr.io/hamza533/mcp-postgres-sheets:1.0.0.')
param image string

@description('Microsoft Entra ID tenant that issues the access tokens.')
param tenantId string = subscription().tenantId

@description('Expected token audience: the Entra app registration\'s client ID (v2 tokens).')
param oauthAudience string

@description('Comma-separated schemas the AI may query.')
param allowedSchemas string = 'public'

@description('Comma-separated spreadsheet IDs the AI may use (empty = Sheets tools return "not allowed").')
param allowedSheetIds string = ''

@description('Keep Sheets write tools hidden (recommended).')
param readOnly bool = true

@description('Tool calls per caller per minute, per replica.')
@minValue(1)
param rateLimitPerMin int = 60

@description('Minimum replicas. 1 keeps the server warm; 0 allows scale-to-zero (cold starts of a few seconds).')
@minValue(0)
@maxValue(10)
param minReplicas int = 1

@description('Maximum replicas for HTTP scaling.')
@minValue(1)
@maxValue(30)
param maxReplicas int = 5

@description('Optional: subnet ID for a VNet-integrated environment, so the app reaches PostgreSQL over a private network. Empty = public egress.')
param infrastructureSubnetId string = ''

@description('Optional custom domain (TLS bound separately), e.g. mcp.contoso.com. Empty = the generated *.azurecontainerapps.io name.')
param customDomain string = ''

@description('Log retention in days for Log Analytics (audit lines live here).')
@minValue(30)
@maxValue(730)
param logRetentionDays int = 90

@description('Tags applied to every resource.')
param tags object = {
  app: 'mcp-postgres-sheets'
}

var suffix = uniqueString(resourceGroup().id, prefix)
var names = {
  logs: '${prefix}-logs-${suffix}'
  appInsights: '${prefix}-ai-${suffix}'
  identity: '${prefix}-id-${suffix}'
  keyVault: take('${prefix}kv${suffix}', 24)
  environment: '${prefix}-env-${suffix}'
  app: '${prefix}-app'
}
// Built-in role: Key Vault Secrets User (read secret values only).
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: names.logs
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: names.appInsights
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
    IngestionMode: 'LogAnalytics'
    DisableLocalAuth: true
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: names.identity
  location: location
  tags: tags
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: names.keyVault
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Allow', bypass: 'AzureServices' }
  }
}

resource secretsReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, identity.id, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: names.environment
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: empty(infrastructureSubnetId)
      ? null
      : {
          infrastructureSubnetId: infrastructureSubnetId
          internal: false
        }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

var publicHost = empty(customDomain) ? '${names.app}.${environment.properties.defaultDomain}' : customDomain

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: names.app
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  dependsOn: [secretsReader]
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8765
        transport: 'auto'
        allowInsecure: false
      }
      // Values live in Key Vault; the app reads them with its managed identity.
      // Create them before the first deployment:
      //   az keyvault secret set --vault-name <kv> --name database-url --value "postgresql://mcp_readonly:…"
      //   az keyvault secret set --vault-name <kv> --name google-service-account-json --file sa.json
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-url'
          identity: identity.id
        }
        {
          name: 'google-service-account-json'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/google-service-account-json'
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'TRANSPORT', value: 'http' }
            { name: 'HTTP_HOST', value: '0.0.0.0' }
            { name: 'HTTP_PORT', value: '8765' }
            { name: 'PUBLIC_URL', value: 'https://${publicHost}' }
            { name: 'OAUTH_ISSUER', value: '${az.environment().authentication.loginEndpoint}${tenantId}/v2.0' }
            { name: 'OAUTH_AUDIENCE', value: oauthAudience }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'GOOGLE_SERVICE_ACCOUNT_JSON', secretRef: 'google-service-account-json' }
            { name: 'ALLOWED_SCHEMAS', value: allowedSchemas }
            { name: 'ALLOWED_SHEET_IDS', value: allowedSheetIds }
            { name: 'READ_ONLY', value: string(readOnly) }
            { name: 'RATE_LIMIT_PER_MIN', value: string(rateLimitPerMin) }
            { name: 'REDACT_ARGS', value: 'true' }
            { name: 'LOG_LEVEL', value: 'INFO' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8765 }
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8765 }
              periodSeconds: 15
              failureThreshold: 3
              initialDelaySeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}

@description('The MCP endpoint to give AI clients.')
output mcpUrl string = 'https://${publicHost}/mcp'

@description('Key Vault to store database-url and google-service-account-json in.')
output keyVaultName string = keyVault.name

@description('Principal ID of the app identity (grant it nothing else).')
output identityPrincipalId string = identity.properties.principalId

@description('Application Insights resource (query the audit lines in its Logs blade).')
output appInsightsName string = appInsights.name
