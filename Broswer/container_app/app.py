"""
Azure Container App - Browser Automation & Computer Use APIs

This FastAPI application provides two endpoints:
1. /api/browser-automation - Uses Azure's managed Playwright Workspaces (no screenshots)
2. /api/computer-use - Uses local Playwright with screenshot capture

Deploy to Azure Container Apps for serverless scaling.
"""
import os
import secrets
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
import uuid
from datetime import datetime

from browser_automation_service import BrowserAutomationService
from computer_use_service import ComputerUseService

app = FastAPI(
    title="Browser Automation & Computer Use API",
    description="Azure AI Foundry powered browser and computer automation APIs",
    version="1.0.0"
)

# In-memory task storage (use Redis/Cosmos DB in production)
tasks = {}


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Reject calls without the shared API key; the endpoints drive a real browser session."""
    expected = os.environ.get("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured on the server")
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


class LoginCredentials(BaseModel):
    """Sign-in details applied with Playwright before the agent starts."""
    username: Optional[str] = None
    password: Optional[str] = None
    # Prefer these: the values are read from container app settings / Key Vault references.
    username_env: Optional[str] = None
    password_env: Optional[str] = None
    username_selector: Optional[str] = None
    password_selector: Optional[str] = None
    submit_selector: Optional[str] = None

    def resolve(self) -> Dict[str, Any]:
        username = self.username or (os.environ.get(self.username_env) if self.username_env else None)
        password = self.password or (os.environ.get(self.password_env) if self.password_env else None)
        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail="Login requires username/password or username_env/password_env that resolve to values"
            )
        return {
            "username": username,
            "password": password,
            "username_selector": self.username_selector,
            "password_selector": self.password_selector,
            "submit_selector": self.submit_selector,
        }


class BrowserAutomationRequest(BaseModel):
    """Request model for browser automation tasks."""
    task: str
    model_deployment_name: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "Go to finance.yahoo.com, search for MSFT, and report the current stock price."
            }
        }


class ComputerUseRequest(BaseModel):
    """Request model for computer use tasks."""
    task: str
    url: Optional[str] = None
    width: int = 1280
    height: int = 800
    save_screenshots: bool = True
    max_steps: int = Field(default=20, ge=1, le=100)
    login: Optional[LoginCredentials] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://identity.example.com/home",
                "task": (
                    "Steps:\n"
                    "1. Look at the tiles on the home page\n"
                    "2. Find the \"My Access\" tile\n"
                    "3. Click on the \"My Access\" tile\n"
                    "4. Confirm you have reached the \"My Access\" page\n\n"
                    "Report what you see on the final page."
                ),
                "login": {
                    "username_env": "PORTAL_USERNAME",
                    "password_env": "PORTAL_PASSWORD"
                },
                "width": 1280,
                "height": 800,
                "max_steps": 20,
                "save_screenshots": True
            }
        }


class TaskResponse(BaseModel):
    """Response model for task submission."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    result: Optional[Any] = None  # Can be dict or str
    error: Optional[str] = None
    screenshots: Optional[List[str]] = None
    created_at: str
    completed_at: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Browser Automation & Computer Use API",
        "version": "1.0.0",
        "endpoints": {
            "browser_automation": "/api/browser-automation",
            "computer_use": "/api/computer-use",
            "task_status": "/api/tasks/{task_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check for container orchestration."""
    return {"status": "healthy"}


@app.post("/api/browser-automation", response_model=TaskResponse, dependencies=[Depends(require_api_key)])
async def browser_automation(request: BrowserAutomationRequest, background_tasks: BackgroundTasks):
    """
    Execute a browser automation task using Azure's managed Playwright Workspaces.
    
    This endpoint uses Azure's BrowserAutomationTool which runs in a managed environment.
    No screenshots are available - results are returned as text.
    
    Suitable for:
    - Web scraping
    - Form filling
    - Data extraction
    - Website testing
    """
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "task_id": task_id,
        "type": "browser_automation",
        "status": "queued",
        "request": request.model_dump(),
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }
    
    # Run task in background
    background_tasks.add_task(
        run_browser_automation_task,
        task_id,
        request.task,
        request.model_deployment_name
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Browser automation task queued for processing"
    )


@app.post("/api/computer-use", response_model=TaskResponse, dependencies=[Depends(require_api_key)])
async def computer_use(request: ComputerUseRequest, background_tasks: BackgroundTasks):
    """
    Execute a computer use task with local Playwright and screenshot capture.
    
    This endpoint uses the Computer Use tool with a local Playwright browser.
    Screenshots are captured after each action and can be retrieved.
    
    Suitable for:
    - Visual automation tasks
    - Screenshot-based workflows
    - Complex multi-step interactions
    - Tasks requiring visual verification
    """
    task_id = str(uuid.uuid4())
    credentials = request.login.resolve() if request.login else None
    
    # Keep credentials out of the stored request payload.
    stored_request = request.model_dump(exclude={"login"})
    stored_request["login"] = bool(credentials)
    
    tasks[task_id] = {
        "task_id": task_id,
        "type": "computer_use",
        "status": "queued",
        "request": stored_request,
        "result": None,
        "error": None,
        "screenshots": [],
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }
    
    # Run task in background
    background_tasks.add_task(
        run_computer_use_task,
        task_id,
        request.task,
        request.url,
        request.width,
        request.height,
        request.save_screenshots,
        request.max_steps,
        credentials
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Computer use task queued for processing"
    )


@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse, dependencies=[Depends(require_api_key)])
async def get_task_status(task_id: str):
    """Get the status and result of a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        screenshots=task.get("screenshots"),
        created_at=task["created_at"],
        completed_at=task.get("completed_at")
    )


@app.get("/api/tasks", dependencies=[Depends(require_api_key)])
async def list_tasks(limit: int = 10):
    """List recent tasks."""
    sorted_tasks = sorted(
        tasks.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    
    return {"tasks": sorted_tasks}


async def run_browser_automation_task(task_id: str, task: str, model_deployment_name: Optional[str]):
    """Background task for browser automation."""
    try:
        tasks[task_id]["status"] = "running"
        
        service = BrowserAutomationService(model_deployment_name=model_deployment_name)
        result = service.run_task(task)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
        tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()


async def run_computer_use_task(
    task_id: str,
    task: str,
    url: Optional[str],
    width: int,
    height: int,
    save_screenshots: bool,
    max_steps: int,
    credentials: Optional[Dict[str, Any]]
):
    """Background task for computer use."""
    try:
        tasks[task_id]["status"] = "running"
        
        service = ComputerUseService(
            width=width,
            height=height,
            save_screenshots=save_screenshots,
            task_id=task_id,
            max_steps=max_steps
        )
        # Await the async run_task method
        result = await service.run_task(task, start_url=url, credentials=credentials)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result.get("result")
        tasks[task_id]["screenshots"] = result.get("screenshots", [])
        tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
