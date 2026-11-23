// Example parameters. Copy, fill in, and deploy with:
//   az deployment group create -g <resource-group> -f deploy/azure/main.bicep -p deploy/azure/main.bicepparam
using 'main.bicep'

param prefix = 'mcpps'
param image = 'ghcr.io/hamza533/mcp-postgres-sheets:0.1.0'
param oauthAudience = '00000000-0000-0000-0000-000000000000' // Entra app registration client ID
param allowedSchemas = 'public'
param allowedSheetIds = ''
param readOnly = true
param minReplicas = 1
param maxReplicas = 5
// param infrastructureSubnetId = '/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Network/virtualNetworks/<vnet>/subnets/<subnet>'
