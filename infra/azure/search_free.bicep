// OPTIONAL Azure AI Search Free tier; service limit/region availability varies.
// Preview and cost-check before manual deployment. No paid LLM services deployed.
targetScope = 'resourceGroup'
param location string = resourceGroup().location
@minLength(3)
@maxLength(12)
param prefix string = 'portrag01'
var serviceName = concat('srch-', prefix, '-', uniqueString(resourceGroup().id))

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: serviceName
  location: location
  sku: { name: 'free' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
  }
}
output searchService string = search.name
