# Browser Automation & Computer Use Container App

This is a containerized API that provides two endpoints for browser automation:

1. **Browser Automation** (`/api/browser-automation`) - Uses Azure's managed Playwright Workspaces
2. **Computer Use** (`/api/computer-use`) - Uses local Playwright with screenshot capture

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application                     │  │
│  │  ┌─────────────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  /api/browser-      │  │  /api/computer-use          │ │  │
│  │  │    automation       │  │  (Local Playwright +        │ │  │
│  │  │  (Azure Managed)    │  │   Screenshots)              │ │  │
│  │  └──────────┬──────────┘  └──────────────┬──────────────┘ │  │
│  └─────────────┼────────────────────────────┼────────────────┘  │
└────────────────┼────────────────────────────┼────────────────────┘
                 │                            │
                 ▼                            ▼
    ┌────────────────────────┐   ┌────────────────────────┐
    │  Azure Playwright      │   │  Chromium Browser      │
    │  Workspaces (Managed)  │   │  (In Container)        │
    └────────────────────────┘   └────────────────────────┘
```

## Endpoints

### POST /api/browser-automation

Execute browser automation tasks using Azure's managed environment.

**Request:**
```json
{
    "task": "Go to finance.yahoo.com, search for MSFT, and report the current stock price."
}
```

**Response:**
```json
{
    "task_id": "uuid",
    "status": "queued",
    "message": "Browser automation task queued for processing"
}
```

### POST /api/computer-use

Execute computer use tasks with local Playwright and screenshot capture.

**Request:**
```json
{
    "task": "Find the email input field and type 'user@example.com'",
    "url": "https://example.com/login",
    "width": 1280,
    "height": 800,
    "save_screenshots": true
}
```

### GET /api/tasks/{task_id}

Get the status and result of a task.

**Response:**
```json
{
    "task_id": "uuid",
    "status": "completed",
    "result": { ... },
    "screenshots": ["path1.png", "path2.png"],
    "created_at": "2025-12-29T10:00:00",
    "completed_at": "2025-12-29T10:01:00"
}
```

## Local Development

### Prerequisites
- Python 3.11+
- Docker (optional, for container testing)

### Setup

1. Create virtual environment:
```bash
python -m venv .venv
.venv\Scripts\Activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

3. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

4. Run the application:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

5. Open API docs: http://localhost:8000/docs

## Docker

### Build
```bash
docker build -t browser-automation-api .
```

### Run
```bash
docker run -p 8000:8000 --env-file .env browser-automation-api
```

## Deploy to Azure Container Apps

### Prerequisites
- Azure CLI installed and logged in
- Azure Container Registry (ACR)

### Steps

1. Create Azure resources:
```bash
# Variables
RESOURCE_GROUP="browser-automation-rg"
LOCATION="eastus2"
ACR_NAME="browserautomationacr"
CONTAINER_APP_ENV="browser-automation-env"
CONTAINER_APP_NAME="browser-automation-api"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create container registry
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic

# Create container app environment
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
```

2. Build and push Docker image:
```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build and push
az acr build --registry $ACR_NAME --image browser-automation-api:latest .
```

3. Deploy Container App:
```bash
az containerapp create \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image $ACR_NAME.azurecr.io/browser-automation-api:latest \
    --target-port 8000 \
    --ingress external \
    --cpu 2 \
    --memory 4Gi \
    --min-replicas 0 \
    --max-replicas 5 \
    --env-vars \
        PROJECT_ENDPOINT=secretref:project-endpoint \
        AZURE_PLAYWRIGHT_CONNECTION_NAME=secretref:playwright-connection \
        MODEL_DEPLOYMENT_NAME=gpt-4o \
        COMPUTER_USE_MODEL_DEPLOYMENT_NAME=computer-use-preview \
        COMPUTER_USE_ENVIRONMENT=browser
```

4. Configure secrets:
```bash
az containerapp secret set \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --secrets \
        project-endpoint="your-project-endpoint" \
        playwright-connection="your-playwright-connection-id"
```

## Comparison: Browser Automation vs Computer Use

| Feature | Browser Automation | Computer Use |
|---------|-------------------|--------------|
| **Execution Environment** | Azure Managed | Local Container |
| **Screenshots** | ❌ Not available | ✅ Saved to Blob Storage |
| **Visual Feedback** | ❌ No | ✅ Yes (via SAS URLs) |
| **Resource Usage** | Low (managed) | Higher (runs browser) |
| **Complexity** | Simple | More complex |
| **Best For** | Data extraction, scraping | Visual tasks, verification |

## Screenshot Storage

Screenshots from Computer Use tasks are stored in Azure Blob Storage:

- **Authentication**: Managed Identity (no connection strings needed)
- **Container**: Configurable via `AZURE_STORAGE_CONTAINER_NAME`
- **Path**: `{task_id}/screenshot_{timestamp}.png`
- **Access**: Time-limited SAS URLs (24 hours) returned in API response

### Required Role Assignment

The Container App's managed identity needs the **Storage Blob Data Contributor** role on the storage account. The deployment script handles this automatically.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint |
| `AZURE_PLAYWRIGHT_CONNECTION_NAME` | Yes* | Playwright Workspaces connection ID |
| `MODEL_DEPLOYMENT_NAME` | Yes | Model deployment for browser automation |
| `COMPUTER_USE_MODEL_DEPLOYMENT_NAME` | No | Model for computer use (defaults to MODEL_DEPLOYMENT_NAME) |
| `COMPUTER_USE_ENVIRONMENT` | No | Environment type: browser, windows, mac, linux |
| `AZURE_STORAGE_ACCOUNT_NAME` | No** | Storage account for screenshots |
| `AZURE_STORAGE_CONTAINER_NAME` | No | Blob container name (default: "screenshots") |

*Required only for browser automation endpoint
**Required for Computer Use screenshot persistence
