# Deploys the Browser Automation / Computer Use API to Azure App Service for Containers.
# Requires Azure CLI and an existing Azure AI Foundry project endpoint.

param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$Location,

    [Parameter(Mandatory = $true)]
    [string]$ProjectEndpoint,

    [Parameter(Mandatory = $true)]
    [string]$AcrName,

    [Parameter(Mandatory = $true)]
    [string]$WebAppName,

    [string]$AppServicePlan = "browser-automation-plan",
    [string]$PlanSku = "P1v3",
    [string]$ImageName = "browser-automation-api",
    [string]$ImageTag = "latest",
    [string]$StorageAccountName,
    [string]$StorageContainerName = "screenshots",
    [string]$ModelDeploymentName = "gpt-4o",
    [string]$ComputerUseModelName = "computer-use-preview",
    [string]$PlaywrightConnectionName
)

$ErrorActionPreference = "Stop"
$image = "$AcrName.azurecr.io/$ImageName`:$ImageTag"

Write-Host "=== App Service (Container) deployment ===" -ForegroundColor Cyan

Write-Host "`n1. Resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location | Out-Null

Write-Host "`n2. Container registry..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --only-show-errors | Out-Null

Write-Host "`n3. Building image in ACR..." -ForegroundColor Yellow
az acr build --registry $AcrName --image "$ImageName`:$ImageTag" .

Write-Host "`n4. App Service plan (Linux)..." -ForegroundColor Yellow
az appservice plan create `
    --name $AppServicePlan `
    --resource-group $ResourceGroup `
    --location $Location `
    --is-linux `
    --sku $PlanSku | Out-Null

Write-Host "`n5. Web app..." -ForegroundColor Yellow
az webapp create `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --name $WebAppName `
    --container-image-name $image | Out-Null

Write-Host "`n6. Managed identity + ACR pull..." -ForegroundColor Yellow
az webapp identity assign --resource-group $ResourceGroup --name $WebAppName | Out-Null
$principalId = az webapp identity show --resource-group $ResourceGroup --name $WebAppName --query principalId -o tsv
$acrId = az acr show --name $AcrName --resource-group $ResourceGroup --query id -o tsv

az role assignment create --assignee $principalId --role "AcrPull" --scope $acrId --only-show-errors | Out-Null
az webapp config set --resource-group $ResourceGroup --name $WebAppName --generic-configurations '{"acrUseManagedIdentityCreds": true}' | Out-Null

Write-Host "`n7. App settings..." -ForegroundColor Yellow
# Generated once here; rotate it from the portal or Key Vault afterwards.
$apiKey = [System.Guid]::NewGuid().ToString("N")

$settings = @(
    "WEBSITES_PORT=8000",
    "PORT=8000",
    "WEBSITES_CONTAINER_START_TIME_LIMIT=600",
    "PROJECT_ENDPOINT=$ProjectEndpoint",
    "MODEL_DEPLOYMENT_NAME=$ModelDeploymentName",
    "COMPUTER_USE_MODEL_DEPLOYMENT_NAME=$ComputerUseModelName",
    "COMPUTER_USE_ENVIRONMENT=browser",
    "API_KEY=$apiKey"
)

if ($StorageAccountName) {
    $settings += "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccountName"
    $settings += "AZURE_STORAGE_CONTAINER_NAME=$StorageContainerName"
}
if ($PlaywrightConnectionName) {
    $settings += "AZURE_PLAYWRIGHT_CONNECTION_NAME=$PlaywrightConnectionName"
}

az webapp config appsettings set --resource-group $ResourceGroup --name $WebAppName --settings $settings | Out-Null

Write-Host "`n8. Always On + health check..." -ForegroundColor Yellow
az webapp config set `
    --resource-group $ResourceGroup `
    --name $WebAppName `
    --always-on true `
    --health-check-path "/health" | Out-Null

if ($StorageAccountName) {
    Write-Host "`n9. Storage role assignment for screenshots..." -ForegroundColor Yellow
    $storageId = az storage account show --name $StorageAccountName --resource-group $ResourceGroup --query id -o tsv
    az role assignment create --assignee $principalId --role "Storage Blob Data Contributor" --scope $storageId --only-show-errors | Out-Null
}

Write-Host "`nGrant the web app identity access to your AI Foundry project:" -ForegroundColor Yellow
Write-Host "  az role assignment create --assignee $principalId --role 'Azure AI User' --scope <foundry-project-resource-id>"

$url = "https://$(az webapp show --resource-group $ResourceGroup --name $WebAppName --query defaultHostName -o tsv)"

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "App URL:  $url"
Write-Host "Swagger:  $url/docs"
Write-Host "API key:  $apiKey  (send as X-API-Key header)" -ForegroundColor Cyan
