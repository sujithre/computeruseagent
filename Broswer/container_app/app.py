"""
Azure Container App - Browser Automation & Computer Use APIs

This FastAPI application provides two endpoints:
1. /api/browser-automation - Uses Azure's managed Playwright Workspaces (no screenshots)
2. /api/computer-use - Uses local Playwright with screenshot capture

Deploy to Azure Container Apps for serverless scaling.
"""
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Any
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "Find the email input field and type 'user@example.com'",
                "url": "https://example.com/login",
                "width": 1280,
                "height": 800,
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


@app.post("/api/browser-automation", response_model=TaskResponse)
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


@app.post("/api/computer-use", response_model=TaskResponse)
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
    
    tasks[task_id] = {
        "task_id": task_id,
        "type": "computer_use",
        "status": "queued",
        "request": request.model_dump(),
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
        request.save_screenshots
    )
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Computer use task queued for processing"
    )


@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
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


@app.get("/api/tasks")
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
    save_screenshots: bool
):
    """Background task for computer use."""
    try:
        tasks[task_id]["status"] = "running"
        
        service = ComputerUseService(
            width=width,
            height=height,
            save_screenshots=save_screenshots,
            task_id=task_id
        )
        # Await the async run_task method
        result = await service.run_task(task, start_url=url)
        
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
