# Computer Use Agent - Azure Container App

A containerized API service that provides AI-powered browser automation and computer use capabilities using Azure AI Foundry Agents. This service enables intelligent web interactions with screenshot capture and visual verification.

---

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Deploy to Azure Container Apps](#deploy-to-azure-container-apps)
- [API Reference](#api-reference)
- [Code Examples](#code-examples)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Description

The Computer Use Agent is an Azure AI Foundry-powered service that enables autonomous browser interactions and computer automation tasks. It leverages:

- **Azure AI Foundry Agents**: AI-powered decision making for complex automation tasks
- **Computer Use Tool**: Enables AI agents to interact with screens through clicks, typing, and scrolling
- **Playwright**: Browser automation with screenshot capture for visual verification
- **Azure Container Apps**: Serverless, scalable deployment with managed infrastructure

### Use Cases

| Use Case | Description |
|----------|-------------|
| **Web Scraping** | Extract data from websites intelligently |
| **Form Automation** | Fill out forms and submit data automatically |
| **Visual Testing** | Capture screenshots for verification and debugging |
| **Multi-step Workflows** | Execute complex sequences of browser interactions |
| **Data Extraction** | Navigate websites and extract structured information |
| **UI Testing** | Automated UI interaction and validation |

---

## Features

| Feature | Description |
|---------|-------------|
| **Browser Automation API** | Uses Azure's managed Playwright Workspaces for serverless browser automation |
| **Computer Use API** | Local Playwright with AI-driven interactions and screenshot capture |
| **Async Task Processing** | Background task execution with status polling |
| **Screenshot Storage** | Automatic screenshot upload to Azure Blob Storage with SAS URLs |
| **Managed Identity** | Secure authentication without credentials |
| **Auto-scaling** | Scale from 0 to 5 replicas based on demand |
| **Health Checks** | Built-in health endpoints for container orchestration |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Azure Container Apps                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Application                        │  │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  /api/browser-          │  │  /api/computer-use          │ │  │
│  │  │    automation           │  │  (Local Playwright +        │ │  │
│  │  │  (Azure Managed)        │  │   Screenshots)              │ │  │
│  │  └───────────┬─────────────┘  └──────────────┬──────────────┘ │  │
│  └──────────────┼───────────────────────────────┼────────────────┘  │
└─────────────────┼───────────────────────────────┼────────────────────┘
                  │                               │
                  ▼                               ▼
     ┌────────────────────────┐    ┌──────────────────────────────┐
     │  Azure Playwright      │    │  Chromium Browser            │
     │  Workspaces (Managed)  │    │  (In Container)              │
     └────────────────────────┘    └──────────────────────────────┘
                                                  │
                                                  ▼
                                   ┌──────────────────────────────┐
                                   │  Azure Blob Storage          │
                                   │  (Screenshots)               │
                                   └──────────────────────────────┘
```

### Component Overview

| Component | Purpose |
|-----------|---------|
| **FastAPI Application** | REST API server handling requests |
| **Browser Automation Service** | Integrates with Azure Playwright Workspaces |
| **Computer Use Service** | Manages local Playwright browser and screenshots |
| **Azure AI Foundry Agent** | AI model that understands and executes tasks |
| **Azure Blob Storage** | Persistent storage for captured screenshots |

---

## Prerequisites

### Azure Resources

| Resource | Description | Required |
|----------|-------------|----------|
| **Azure Subscription** | Active Azure subscription with billing enabled | ✅ |
| **Azure AI Foundry Project** | AI project with agents capability enabled | ✅ |
| **Playwright Connection** | Microsoft Playwright Workspaces connection configured in AI Foundry | ✅ |
| **Model Deployment (GPT-4o)** | GPT-4o or compatible model deployed in AI Foundry | ✅ |
| **Computer Use Model** | Model deployment with Computer Use capability (e.g., `computer-use-preview`) | ✅ |
| **Azure Storage Account** | For storing screenshots (optional but recommended) | ⚠️ |

### Tools & Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Azure CLI** | 2.50+ | Azure resource management and deployment |
| **Docker** | 20.10+ | Local container testing (optional) |
| **Python** | 3.11+ | Local development and testing |
| **PowerShell** | 5.1+ / 7+ | Running deployment scripts (Windows) |
| **Git** | Latest | Source control |

### Azure CLI Extensions

Install required Azure CLI extensions before deployment:

```powershell
# Install/upgrade Container Apps extension
az extension add --name containerapp --upgrade

# Install/upgrade Storage extension
az extension add --name storage-preview --upgrade

# Login to Azure
az login
```

### Azure AI Foundry Setup

1. **Create an AI Foundry Project**:
   - Navigate to [Azure AI Foundry Portal](https://ai.azure.com)
   - Create a new project or select an existing one
   - Note the **Project Endpoint** URL from the overview page

2. **Configure Playwright Connection**:
   - Go to **Management Center** → **Connected Resources**
   - Click **+ New Connection**
   - Select **Microsoft Playwright Workspaces**
   - Configure and save the connection
   - Note the **Connection Name** for deployment

3. **Deploy Required Models**:
   - Navigate to **Models + Endpoints**
   - Deploy `gpt-4o` for browser automation tasks
   - Deploy a computer-use capable model if available (e.g., `computer-use-preview`)

---

## Local Development

### Setup Steps

1. **Clone and navigate to the project**:
   ```powershell
   cd container_app
   ```

2. **Create and activate virtual environment**:

   **Windows (PowerShell)**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **Linux/Mac**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

5. **Configure environment variables**:

   Create a `.env` file in the `container_app` directory:

   ```env
   # Azure AI Foundry Configuration
   PROJECT_ENDPOINT=https://your-project.api.azureml.ms
   AZURE_PLAYWRIGHT_CONNECTION_NAME=your-playwright-connection-name
   MODEL_DEPLOYMENT_NAME=gpt-4o
   
   # Computer Use Configuration
   COMPUTER_USE_MODEL_DEPLOYMENT_NAME=computer-use-preview
   COMPUTER_USE_ENVIRONMENT=browser
   
   # Optional: Azure Storage for Screenshots
   AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
   AZURE_STORAGE_CONTAINER_NAME=screenshots
   ```

6. **Run the development server**:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**:
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Local Docker Testing

Build and run the container locally for testing:

```powershell
# Build the Docker image
docker build -t browser-automation-api:local .

# Run the container with environment variables
docker run -p 8000:8000 `
  -e PROJECT_ENDPOINT="https://your-project.api.azureml.ms" `
  -e AZURE_PLAYWRIGHT_CONNECTION_NAME="your-connection" `
  -e MODEL_DEPLOYMENT_NAME="gpt-4o" `
  -e COMPUTER_USE_MODEL_DEPLOYMENT_NAME="computer-use-preview" `
  -e COMPUTER_USE_ENVIRONMENT="browser" `
  browser-automation-api:local
```

---

## Deploy to Azure Container Apps

### Quick Deployment (Recommended)

Use the provided PowerShell deployment script for automated deployment:

```powershell
.\deploy.ps1 `
  -ResourceGroup "browser-automation-rg" `
  -Location "eastus" `
  -ProjectEndpoint "https://your-project.api.azureml.ms" `
  -PlaywrightConnectionName "your-playwright-connection"
```

### Deployment Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `ResourceGroup` | ✅ | - | Azure resource group name |
| `Location` | ✅ | - | Azure region (e.g., `eastus`, `westus2`, `westeurope`) |
| `ProjectEndpoint` | ✅ | - | Azure AI Foundry project endpoint URL |
| `PlaywrightConnectionName` | ✅ | - | Playwright connection name from AI Foundry |
| `AcrName` | ❌ | `browserautomationacr` | Azure Container Registry name (must be globally unique) |
| `ContainerAppEnv` | ❌ | `browser-automation-env` | Container Apps environment name |
| `ContainerAppName` | ❌ | `browser-automation-api` | Container App name |
| `StorageAccountName` | ❌ | `browserautomationsa` | Storage account for screenshots (must be globally unique) |
| `StorageContainerName` | ❌ | `screenshots` | Blob container name |
| `ModelDeploymentName` | ❌ | `gpt-4o` | Model for browser automation |
| `ComputerUseModelName` | ❌ | `computer-use-preview` | Model for computer use tasks |

### What the Deployment Script Creates

1. **Resource Group** - Container for all resources
2. **Storage Account** - For screenshot storage
3. **Blob Container** - For organizing screenshots
4. **Azure Container Registry** - For storing Docker images
5. **Container Apps Environment** - Managed environment for containers
6. **Container App** - The deployed API with managed identity
7. **Role Assignments** - Storage Blob Data Contributor for managed identity

### Manual Deployment Steps

If you prefer manual deployment or need more control:

#### Step 1: Create Resource Group
```powershell
az group create --name browser-automation-rg --location eastus
```

#### Step 2: Create Storage Account
```powershell
az storage account create `
  --name browserautomationsa `
  --resource-group browser-automation-rg `
  --location eastus `
  --sku Standard_LRS `
  --kind StorageV2

az storage container create `
  --name screenshots `
  --account-name browserautomationsa
```

#### Step 3: Create Container Registry
```powershell
az acr create `
  --resource-group browser-automation-rg `
  --name browserautomationacr `
  --sku Basic

az acr update --name browserautomationacr --admin-enabled true
```

#### Step 4: Build and Push Docker Image
```powershell
az acr login --name browserautomationacr
az acr build --registry browserautomationacr --image browser-automation-api:latest .
```

#### Step 5: Create Container Apps Environment
```powershell
az containerapp env create `
  --name browser-automation-env `
  --resource-group browser-automation-rg `
  --location eastus
```

#### Step 6: Deploy Container App
```powershell
$acrPassword = $(az acr credential show --name browserautomationacr --query "passwords[0].value" -o tsv)

az containerapp create `
  --name browser-automation-api `
  --resource-group browser-automation-rg `
  --environment browser-automation-env `
  --image browserautomationacr.azurecr.io/browser-automation-api:latest `
  --registry-server browserautomationacr.azurecr.io `
  --registry-username browserautomationacr `
  --registry-password $acrPassword `
  --target-port 8000 `
  --ingress external `
  --cpu 2 --memory 4Gi `
  --min-replicas 0 --max-replicas 5 `
  --system-assigned `
  --env-vars `
    PROJECT_ENDPOINT="https://your-project.api.azureml.ms" `
    AZURE_PLAYWRIGHT_CONNECTION_NAME="your-connection" `
    MODEL_DEPLOYMENT_NAME="gpt-4o" `
    COMPUTER_USE_MODEL_DEPLOYMENT_NAME="computer-use-preview" `
    COMPUTER_USE_ENVIRONMENT="browser" `
    AZURE_STORAGE_ACCOUNT_NAME="browserautomationsa" `
    AZURE_STORAGE_CONTAINER_NAME="screenshots"
```

#### Step 7: Configure Managed Identity Permissions
```powershell
$principalId = $(az containerapp show --name browser-automation-api --resource-group browser-automation-rg --query "identity.principalId" -o tsv)
$storageId = $(az storage account show --name browserautomationsa --resource-group browser-automation-rg --query "id" -o tsv)

az role assignment create `
  --assignee $principalId `
  --role "Storage Blob Data Contributor" `
  --scope $storageId
```

### Post-Deployment Verification

After deployment, verify the service is running:

```powershell
# Get the application URL
$appUrl = $(az containerapp show --name browser-automation-api --resource-group browser-automation-rg --query "properties.configuration.ingress.fqdn" -o tsv)

Write-Host "Application URL: https://$appUrl"
Write-Host "API Documentation: https://$appUrl/docs"

# Test health endpoint
Invoke-RestMethod -Uri "https://$appUrl/health"
```

---

## API Reference

### Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://your-app.azurecontainerapps.io`

---

### Health Endpoints

#### `GET /`

Returns service health status and available endpoints.

**Response:**
```json
{
  "status": "healthy",
  "service": "Browser Automation & Computer Use API",
  "version": "1.0.0",
  "endpoints": {
    "browser_automation": "/api/browser-automation",
    "computer_use": "/api/computer-use",
    "task_status": "/api/tasks/{task_id}"
  }
}
```

#### `GET /health`

Simple health check for container orchestration.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Browser Automation Endpoint

#### `POST /api/browser-automation`

Execute browser automation tasks using Azure's managed Playwright Workspaces. Best for data extraction and web scraping tasks.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task` | string | ✅ | Natural language description of the automation task |
| `model_deployment_name` | string | ❌ | Override default model deployment |

**Example Request:**
```bash
curl -X POST "https://your-app.azurecontainerapps.io/api/browser-automation" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Go to finance.yahoo.com, search for MSFT, and report the current stock price."
  }'
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Browser automation task queued for processing"
}
```

**Best For:**
- Web scraping and data extraction
- Form filling
- Website testing
- Data collection tasks

---

### Computer Use Endpoint

#### `POST /api/computer-use`

Execute computer use tasks with local Playwright browser and screenshot capture. Ideal for visual automation tasks requiring verification.

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `task` | string | ✅ | - | Natural language task description |
| `url` | string | ❌ | `null` | Initial URL to navigate to |
| `width` | integer | ❌ | `1280` | Browser viewport width in pixels |
| `height` | integer | ❌ | `800` | Browser viewport height in pixels |
| `save_screenshots` | boolean | ❌ | `true` | Save screenshots to blob storage |

**Example Request:**
```bash
curl -X POST "https://your-app.azurecontainerapps.io/api/computer-use" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Find the email input field and type '\''user@example.com'\''",
    "url": "https://example.com/login",
    "width": 1280,
    "height": 800,
    "save_screenshots": true
  }'
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "queued",
  "message": "Computer use task queued for processing"
}
```

**Best For:**
- Visual automation tasks
- Screenshot-based workflows
- Complex multi-step interactions
- Tasks requiring visual verification
- UI testing and validation

---

### Task Status Endpoint

#### `GET /api/tasks/{task_id}`

Retrieve the status and result of a previously submitted task.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string (UUID) | Unique identifier of the task |

**Example Request:**
```bash
curl "https://your-app.azurecontainerapps.io/api/tasks/550e8400-e29b-41d4-a716-446655440000"
```

**Response (Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "response": "The current stock price of MSFT is $425.32"
  },
  "error": null,
  "screenshots": [
    "https://storageaccount.blob.core.windows.net/screenshots/task_123/screenshot_1704456000000.png?sv=...",
    "https://storageaccount.blob.core.windows.net/screenshots/task_123/screenshot_1704456005000.png?sv=..."
  ],
  "created_at": "2026-01-05T10:00:00",
  "completed_at": "2026-01-05T10:01:30"
}
```

**Response (Failed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "result": null,
  "error": "Timeout waiting for page to load",
  "screenshots": [],
  "created_at": "2026-01-05T10:00:00",
  "completed_at": "2026-01-05T10:02:00"
}
```

**Task Status Values:**

| Status | Description |
|--------|-------------|
| `queued` | Task is waiting to be processed |
| `running` | Task is currently executing |
| `completed` | Task finished successfully |
| `failed` | Task failed with an error |

---

### List Tasks Endpoint

#### `GET /api/tasks`

List recent tasks with optional limit.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `10` | Maximum number of tasks to return |

**Example Request:**
```bash
curl "https://your-app.azurecontainerapps.io/api/tasks?limit=5"
```

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "type": "computer_use",
      "status": "completed",
      "request": { ... },
      "result": { ... },
      "created_at": "2026-01-05T10:00:00",
      "completed_at": "2026-01-05T10:01:30"
    },
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "browser_automation",
      "status": "completed",
      "request": { ... },
      "result": { ... },
      "created_at": "2026-01-05T09:55:00",
      "completed_at": "2026-01-05T09:56:00"
    }
  ]
}
```

---

### API Comparison

| Feature | Browser Automation | Computer Use |
|---------|-------------------|--------------|
| **Endpoint** | `/api/browser-automation` | `/api/computer-use` |
| **Execution** | Azure Managed | Local Container |
| **Screenshots** | ❌ Not available | ✅ Saved to Blob Storage |
| **Visual Feedback** | ❌ No | ✅ SAS URLs provided |
| **Resource Usage** | Low (managed) | Higher (runs browser) |
| **Best For** | Data extraction | Visual verification |

---

## Code Examples

### Python Client Example

```python
import requests
import time
import json

class BrowserAutomationClient:
    """Client for interacting with the Browser Automation API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def submit_browser_automation_task(self, task: str) -> dict:
        """Submit a browser automation task."""
        url = f"{self.base_url}/api/browser-automation"
        response = requests.post(url, json={"task": task})
        response.raise_for_status()
        return response.json()
    
    def submit_computer_use_task(self, task: str, url: str = None, 
                                 width: int = 1280, height: int = 800) -> dict:
        """Submit a computer use task."""
        endpoint = f"{self.base_url}/api/computer-use"
        payload = {
            "task": task,
            "width": width,
            "height": height,
            "save_screenshots": True
        }
        if url:
            payload["url"] = url
        
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> dict:
        """Get the status of a task."""
        url = f"{self.base_url}/api/tasks/{task_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def wait_for_task(self, task_id: str, timeout: int = 300, poll_interval: int = 5) -> dict:
        """Wait for a task to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status["status"] in ["completed", "failed"]:
                return status
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")

# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = BrowserAutomationClient("https://your-app.azurecontainerapps.io")
    
    # Submit a browser automation task
    print("Submitting browser automation task...")
    response = client.submit_browser_automation_task(
        "Go to finance.yahoo.com, search for MSFT, and report the current stock price."
    )
    task_id = response["task_id"]
    print(f"Task ID: {task_id}")
    
    # Wait for completion
    print("Waiting for task to complete...")
    result = client.wait_for_task(task_id)
    
    if result["status"] == "completed":
        print("Task completed successfully!")
        print(f"Result: {result['result']}")
    else:
        print(f"Task failed: {result['error']}")
```

### PowerShell Client Example

```powershell
# Browser Automation Client Functions
function Submit-BrowserAutomationTask {
    param(
        [string]$BaseUrl,
        [string]$Task
    )
    
    $uri = "$BaseUrl/api/browser-automation"
    $body = @{ task = $Task } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri $uri -Method POST -Body $body -ContentType "application/json"
    return $response
}

function Submit-ComputerUseTask {
    param(
        [string]$BaseUrl,
        [string]$Task,
        [string]$Url = $null,
        [int]$Width = 1280,
        [int]$Height = 800
    )
    
    $uri = "$BaseUrl/api/computer-use"
    $body = @{
        task = $Task
        width = $Width
        height = $Height
        save_screenshots = $true
    }
    
    if ($Url) {
        $body.url = $Url
    }
    
    $jsonBody = $body | ConvertTo-Json
    $response = Invoke-RestMethod -Uri $uri -Method POST -Body $jsonBody -ContentType "application/json"
    return $response
}

function Get-TaskStatus {
    param(
        [string]$BaseUrl,
        [string]$TaskId
    )
    
    $uri = "$BaseUrl/api/tasks/$TaskId"
    $response = Invoke-RestMethod -Uri $uri -Method GET
    return $response
}

function Wait-ForTask {
    param(
        [string]$BaseUrl,
        [string]$TaskId,
        [int]$TimeoutSeconds = 300,
        [int]$PollIntervalSeconds = 5
    )
    
    $startTime = Get-Date
    
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        $status = Get-TaskStatus -BaseUrl $BaseUrl -TaskId $TaskId
        
        if ($status.status -eq "completed" -or $status.status -eq "failed") {
            return $status
        }
        
        Start-Sleep -Seconds $PollIntervalSeconds
    }
    
    throw "Task $TaskId did not complete within $TimeoutSeconds seconds"
}

# Usage Example
$baseUrl = "https://your-app.azurecontainerapps.io"

# Submit a computer use task
Write-Host "Submitting computer use task..." -ForegroundColor Cyan
$response = Submit-ComputerUseTask -BaseUrl $baseUrl `
    -Task "Navigate to the login page and find the email input field" `
    -Url "https://example.com/login"

$taskId = $response.task_id
Write-Host "Task ID: $taskId" -ForegroundColor Green

# Wait for completion
Write-Host "Waiting for task to complete..." -ForegroundColor Cyan
$result = Wait-ForTask -BaseUrl $baseUrl -TaskId $taskId

if ($result.status -eq "completed") {
    Write-Host "Task completed successfully!" -ForegroundColor Green
    Write-Host "Result: $($result.result | ConvertTo-Json -Depth 10)" -ForegroundColor White
    
    if ($result.screenshots) {
        Write-Host "`nScreenshots:" -ForegroundColor Cyan
        $result.screenshots | ForEach-Object { Write-Host "  - $_" }
    }
} else {
    Write-Host "Task failed: $($result.error)" -ForegroundColor Red
}
```

### cURL Examples

#### Browser Automation

```bash
# Submit task
curl -X POST "https://your-app.azurecontainerapps.io/api/browser-automation" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Go to github.com and search for Azure AI projects"
  }'

# Response: {"task_id":"abc-123","status":"queued",...}

# Check status
curl "https://your-app.azurecontainerapps.io/api/tasks/abc-123"
```

#### Computer Use with Screenshots

```bash
# Submit task
curl -X POST "https://your-app.azurecontainerapps.io/api/computer-use" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Click on the search button and type Azure",
    "url": "https://example.com",
    "width": 1920,
    "height": 1080,
    "save_screenshots": true
  }'

# Check status with screenshots
curl "https://your-app.azurecontainerapps.io/api/tasks/def-456"
```

### JavaScript/TypeScript Example

```typescript
interface TaskResponse {
  task_id: string;
  status: string;
  message: string;
}

interface TaskStatus {
  task_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
  screenshots?: string[];
  created_at: string;
  completed_at?: string;
}

class BrowserAutomationClient {
  constructor(private baseUrl: string) {}

  async submitBrowserAutomation(task: string): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/browser-automation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
    });
    return response.json();
  }

  async submitComputerUse(
    task: string,
    url?: string,
    width = 1280,
    height = 800
  ): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/computer-use`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, url, width, height, save_screenshots: true })
    });
    return response.json();
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${this.baseUrl}/api/tasks/${taskId}`);
    return response.json();
  }

  async waitForTask(
    taskId: string,
    timeout = 300000,
    pollInterval = 5000
  ): Promise<TaskStatus> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = await this.getTaskStatus(taskId);

      if (status.status === 'completed' || status.status === 'failed') {
        return status;
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Task ${taskId} did not complete within ${timeout}ms`);
  }
}

// Usage
const client = new BrowserAutomationClient('https://your-app.azurecontainerapps.io');

(async () => {
  const response = await client.submitBrowserAutomation(
    'Search for Python tutorials on GitHub'
  );
  
  console.log('Task submitted:', response.task_id);
  
  const result = await client.waitForTask(response.task_id);
  console.log('Result:', result.result);
})();
```

### Project Structure Reference

```
Browser/
├── container_app/
│   ├── app.py                          # FastAPI application
│   ├── browser_automation_service.py   # Browser automation logic
│   ├── computer_use_service.py         # Computer use logic
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Container configuration
│   ├── deploy.ps1                      # Deployment script
│   └── DOCUMENTATION.md                # This file
├── browser_automation_agent.py         # Standalone browser automation agent
├── computer_use_agent.py               # Standalone computer use agent
├── config.py                           # Configuration loader
├── requirements.txt                    # Root dependencies
└── README.md                           # Root readme
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint URL | `https://your-project.api.azureml.ms` |
| `AZURE_PLAYWRIGHT_CONNECTION_NAME` | Playwright connection name in AI Foundry | `playwright-workspace-connection` |
| `MODEL_DEPLOYMENT_NAME` | Model deployment for browser automation | `gpt-4o` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPUTER_USE_MODEL_DEPLOYMENT_NAME` | Same as `MODEL_DEPLOYMENT_NAME` | Model for computer use tasks |
| `COMPUTER_USE_ENVIRONMENT` | `browser` | Environment type: `windows`, `mac`, `linux`, `browser` |
| `AZURE_STORAGE_ACCOUNT_NAME` | - | Storage account for screenshots |
| `AZURE_STORAGE_CONTAINER_NAME` | `screenshots` | Blob container for screenshots |

---

## Troubleshooting

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| **401 Authentication Error** | Invalid or missing credentials | Verify `PROJECT_ENDPOINT` is correct and managed identity has access |
| **Container fails to start** | Missing environment variables | Check all required variables are set |
| **Screenshots not saving** | Missing storage permissions | Ensure managed identity has Storage Blob Data Contributor role |
| **Model deployment not found** | Incorrect model name | Verify model name matches exactly in AI Foundry portal |
| **Playwright timeout** | Page load too slow | Increase container CPU/memory or simplify task |
| **Task stuck in queued** | Worker process crashed | Check container logs and restart if needed |

### Viewing Container Logs

```powershell
# Follow live logs
az containerapp logs show `
  --name browser-automation-api `
  --resource-group browser-automation-rg `
  --follow

# Get recent logs
az containerapp logs show `
  --name browser-automation-api `
  --resource-group browser-automation-rg `
  --tail 100
```

### Checking Deployment Status

```powershell
az containerapp show `
  --name browser-automation-api `
  --resource-group browser-automation-rg `
  --query "{status:properties.runningStatus, url:properties.configuration.ingress.fqdn, replicas:properties.template.scale}"
```

### Restarting the Container App

```powershell
az containerapp revision restart `
  --name browser-automation-api `
  --resource-group browser-automation-rg `
  --revision $(az containerapp revision list --name browser-automation-api --resource-group browser-automation-rg --query "[0].name" -o tsv)
```

### Testing API Locally

```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Submit a test task
$body = @{
    task = "Go to google.com and search for Azure"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/browser-automation" -Method POST -Body $body -ContentType "application/json"
```

---

## References

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Computer Use Tool Guide](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools-classic/computer-use)
- [Browser Automation Samples](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools-classic/browser-automation-samples)
- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [Azure Blob Storage Documentation](https://learn.microsoft.com/azure/storage/blobs/)
