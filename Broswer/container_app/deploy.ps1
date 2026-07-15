# Azure deployment script for Browser Automation Container App
# Run this script in Azure Cloud Shell or with Azure CLI installed

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [Parameter(Mandatory=$true)]
    [string]$ProjectEndpoint,
    
    [Parameter(Mandatory=$true)]
    [string]$PlaywrightConnectionName,
    
    [string]$AcrName = "browserautomationacr",
    [string]$ContainerAppEnv = "browser-automation-env",
    [string]$ContainerAppName = "browser-automation-api",
    [string]$StorageAccountName = "browserautomationsa",
    [string]$StorageContainerName = "screenshots",
    [string]$ModelDeploymentName = "gpt-4o",
    [string]$ComputerUseModelName = "computer-use-preview"
)

Write-Host "=== Browser Automation Container App Deployment ===" -ForegroundColor Cyan

# Create resource group
Write-Host "`n1. Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Create storage account for screenshots
Write-Host "`n2. Creating Storage Account for screenshots..." -ForegroundColor Yellow
az storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --allow-blob-public-access false

# Create blob container
Write-Host "`n3. Creating blob container..." -ForegroundColor Yellow
az storage container create `
    --name $StorageContainerName `
    --account-name $StorageAccountName `
    --auth-mode login

# Create container registry
Write-Host "`n4. Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic

# Enable admin access for ACR
az acr update --name $AcrName --admin-enabled true

# Get ACR credentials
$acrPassword = $(az acr credential show --name $AcrName --query "passwords[0].value" -o tsv)

# Create container app environment
Write-Host "`n5. Creating Container Apps environment..." -ForegroundColor Yellow
az containerapp env create `
    --name $ContainerAppEnv `
    --resource-group $ResourceGroup `
    --location $Location

# Build and push image
Write-Host "`n6. Building and pushing Docker image..." -ForegroundColor Yellow
az acr login --name $AcrName
az acr build --registry $AcrName --image browser-automation-api:latest .

# Deploy container app with system-assigned managed identity
Write-Host "`n7. Deploying Container App with Managed Identity..." -ForegroundColor Yellow
az containerapp create `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --environment $ContainerAppEnv `
    --image "$AcrName.azurecr.io/browser-automation-api:latest" `
    --registry-server "$AcrName.azurecr.io" `
    --registry-username $AcrName `
    --registry-password $acrPassword `
    --target-port 8000 `
    --ingress external `
    --cpu 2 `
    --memory 4Gi `
    --min-replicas 0 `
    --max-replicas 5 `
    --system-assigned `
    --env-vars `
        "PROJECT_ENDPOINT=$ProjectEndpoint" `
        "AZURE_PLAYWRIGHT_CONNECTION_NAME=$PlaywrightConnectionName" `
        "MODEL_DEPLOYMENT_NAME=$ModelDeploymentName" `
        "COMPUTER_USE_MODEL_DEPLOYMENT_NAME=$ComputerUseModelName" `
        "COMPUTER_USE_ENVIRONMENT=browser" `
        "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccountName" `
        "AZURE_STORAGE_CONTAINER_NAME=$StorageContainerName"

# Get the managed identity principal ID
Write-Host "`n8. Configuring Managed Identity permissions..." -ForegroundColor Yellow
$principalId = $(az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "identity.principalId" -o tsv)
$storageAccountId = $(az storage account show --name $StorageAccountName --resource-group $ResourceGroup --query "id" -o tsv)

# Assign Storage Blob Data Contributor role to the managed identity
az role assignment create `
    --assignee $principalId `
    --role "Storage Blob Data Contributor" `
    --scope $storageAccountId

Write-Host "  Assigned 'Storage Blob Data Contributor' role to Container App managed identity" -ForegroundColor Green

# Get the app URL
$appUrl = $(az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv)

Write-Host "`n=== Deployment Complete! ===" -ForegroundColor Green
Write-Host "Container App URL: https://$appUrl" -ForegroundColor Cyan
Write-Host "API Documentation: https://$appUrl/docs" -ForegroundColor Cyan
Write-Host "`nEndpoints:"
Write-Host "  - Browser Automation: POST https://$appUrl/api/browser-automation"
Write-Host "  - Computer Use: POST https://$appUrl/api/computer-use"
Write-Host "  - Task Status: GET https://$appUrl/api/tasks/{task_id}"
Write-Host "`nScreenshots Storage:"
Write-Host "  - Storage Account: $StorageAccountName"
Write-Host "  - Container: $StorageContainerName"
Write-Host "  - Authentication: Managed Identity (Storage Blob Data Contributor)"
