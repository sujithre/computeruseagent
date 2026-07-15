"""
Computer Use Service

Uses local Playwright browser with screenshot capture for Computer Use agent.
Screenshots are saved to Azure Blob Storage using Managed Identity.
"""
import os
import time
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    MessageRole,
    RunStepToolCallDetails,
    RunStepComputerUseToolCall,
    ComputerUseTool,
    ComputerToolOutput,
    MessageInputContentBlock,
    MessageImageUrlParam,
    MessageInputTextBlock,
    MessageInputImageUrlBlock,
    RequiredComputerUseToolCall,
    SubmitToolOutputsAction,
)
from azure.ai.agents.models._models import ComputerScreenshot, TypeAction, ClickAction, ScrollAction
from azure.identity import DefaultAzureCredential
from playwright.async_api import async_playwright, Page, Browser

# Azure Blob Storage imports
try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    BLOB_STORAGE_AVAILABLE = True
except ImportError:
    BLOB_STORAGE_AVAILABLE = False


class ComputerUseService:
    """Service for running computer use tasks with Playwright and screenshot capture."""
    
    def __init__(
        self,
        width: int = 1280,
        height: int = 800,
        save_screenshots: bool = True,
        task_id: Optional[str] = None
    ):
        """
        Initialize the Computer Use service.
        
        Args:
            width: Browser viewport width.
            height: Browser viewport height.
            save_screenshots: Whether to save screenshots.
            task_id: Unique task ID for organizing screenshots.
        """
        self.width = width
        self.height = height
        self.save_screenshots = save_screenshots
        self.task_id = task_id or str(int(time.time()))
        
        self.project_endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.model_name = os.environ.get("COMPUTER_USE_MODEL_DEPLOYMENT_NAME", 
                                         os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o"))
        self.environment = os.environ.get("COMPUTER_USE_ENVIRONMENT", "browser")
        
        if not self.project_endpoint:
            raise ValueError("PROJECT_ENDPOINT environment variable is required")
        
        # Azure Blob Storage configuration
        self.storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "screenshots")
        self.use_blob_storage = bool(self.storage_account_name) and BLOB_STORAGE_AVAILABLE
        
        # Initialize blob client with managed identity if configured
        self.blob_service_client = None
        self.container_client = None
        if self.use_blob_storage:
            self._init_blob_storage()
        
        # Screenshot storage
        self.screenshots: List[str] = []
        self.screenshot_dir = os.path.join("/tmp", "screenshots", self.task_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Playwright resources
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    def _init_blob_storage(self):
        """Initialize Azure Blob Storage client with Managed Identity."""
        try:
            # Use DefaultAzureCredential which supports Managed Identity
            credential = DefaultAzureCredential()
            account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
            
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Ensure container exists
            try:
                self.container_client.get_container_properties()
            except Exception:
                # Container doesn't exist, create it
                self.container_client.create_container()
                
            print(f"Blob storage initialized: {account_url}/{self.container_name}")
        except Exception as e:
            print(f"Warning: Failed to initialize blob storage: {e}")
            self.use_blob_storage = False
    
    async def _start_browser(self, url: Optional[str] = None):
        """Start the Playwright browser (async)."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)  # Always headless in container
        self.page = await self.browser.new_page(viewport={"width": self.width, "height": self.height})
        
        if url:
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
    
    async def _stop_browser(self):
        """Stop the Playwright browser (async)."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _take_screenshot(self) -> tuple:
        """Take a screenshot and return the path/URL and base64 data (async)."""
        # Ensure screenshot directory exists
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        await self.page.screenshot(path=filepath)
        
        # Read file for base64 BEFORE potentially deleting it
        screenshot_base64 = self._image_to_base64(filepath)
        
        if self.save_screenshots:
            if self.use_blob_storage:
                # Upload to Azure Blob Storage
                blob_url = self._upload_to_blob(filepath, filename)
                self.screenshots.append(blob_url)
            else:
                self.screenshots.append(filepath)
        
        return filepath, screenshot_base64
    
    def _upload_to_blob(self, filepath: str, filename: str) -> str:
        """
        Upload screenshot to Azure Blob Storage using Managed Identity.
        
        Args:
            filepath: Local path to the screenshot file.
            filename: Name for the blob.
            
        Returns:
            URL to access the uploaded blob (with SAS token for time-limited access).
        """
        try:
            # Create blob path: {task_id}/{filename}
            blob_name = f"{self.task_id}/{filename}"
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Upload the file
            with open(filepath, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            # Generate a SAS URL for the blob (valid for 24 hours)
            # Note: For User Delegation SAS with managed identity, we need user delegation key
            try:
                # Get user delegation key (requires managed identity)
                delegation_key = self.blob_service_client.get_user_delegation_key(
                    key_start_time=datetime.utcnow(),
                    key_expiry_time=datetime.utcnow() + timedelta(hours=24)
                )
                
                sas_token = generate_blob_sas(
                    account_name=self.storage_account_name,
                    container_name=self.container_name,
                    blob_name=blob_name,
                    user_delegation_key=delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=24)
                )
                
                blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            except Exception as e:
                # If SAS generation fails, return the direct URL (requires public access or AAD auth)
                print(f"Warning: Could not generate SAS token: {e}")
                blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            
            print(f"  Uploaded screenshot to blob: {blob_name}")
            
            # Clean up local file after upload
            try:
                os.remove(filepath)
            except Exception:
                pass
            
            return blob_url
            
        except Exception as e:
            print(f"Warning: Failed to upload to blob storage: {e}")
            # Fall back to local path
            return filepath
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    async def _execute_action(self, action):
        """Execute a computer use action in the browser (async)."""
        if isinstance(action, ClickAction):
            button = getattr(action, 'button', 'left')
            if hasattr(button, 'value'):
                button = button.value
            await self.page.mouse.click(action.x, action.y, button=button)
            await asyncio.sleep(0.5)
        
        elif isinstance(action, TypeAction):
            await self.page.keyboard.type(action.text)
            await asyncio.sleep(0.3)
        
        elif isinstance(action, ScrollAction):
            await self.page.mouse.move(action.x, action.y)
            await self.page.mouse.wheel(action.scroll_x, action.scroll_y)
            await asyncio.sleep(0.3)
    
    async def run_task(self, task: str, start_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a computer use task (async).
        
        Args:
            task: The task description for the computer use agent.
            start_url: Optional URL to navigate to before starting.
            
        Returns:
            Dictionary containing the result and screenshot paths.
        """
        result = {
            "result": None,
            "screenshots": [],
            "actions": []
        }
        
        try:
            # Start browser
            await self._start_browser(url=start_url)
            
            # Take initial screenshot
            initial_screenshot_path, initial_screenshot_base64 = await self._take_screenshot()
            
            # Initialize Azure AI client
            project_client = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=DefaultAzureCredential()
            )
            
            computer_use = ComputerUseTool(
                display_width=self.width,
                display_height=self.height,
                environment=self.environment
            )
            
            with project_client:
                agents_client = project_client.agents
                
                # Create agent
                agent = agents_client.create_agent(
                    model=self.model_name,
                    name="computer-use-agent",
                    instructions="""
                        You are a computer automation assistant.
                        Use the computer_use_preview tool to interact with the screen when needed.
                        Analyze screenshots carefully before taking actions.
                        Be precise with click coordinates and typing actions.
                    """,
                    tools=computer_use.definitions,
                )
                
                try:
                    # Create thread
                    thread = agents_client.threads.create()
                    
                    # Prepare initial message with screenshot
                    img_url = f"data:image/png;base64,{initial_screenshot_base64}"
                    url_param = MessageImageUrlParam(url=img_url, detail="high")
                    
                    content_blocks: List[MessageInputContentBlock] = [
                        MessageInputTextBlock(text=task),
                        MessageInputImageUrlBlock(image_url=url_param),
                    ]
                    
                    # Create message
                    agents_client.messages.create(
                        thread_id=thread.id,
                        role=MessageRole.USER,
                        content=content_blocks
                    )
                    
                    # Create run
                    run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
                    
                    # Process the run loop
                    max_iterations = 20
                    iteration = 0
                    
                    while run.status in ["queued", "in_progress", "requires_action"] and iteration < max_iterations:
                        await asyncio.sleep(1)
                        run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
                        iteration += 1
                        
                        if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
                            tool_calls = run.required_action.submit_tool_outputs.tool_calls
                            
                            if not tool_calls:
                                agents_client.runs.cancel(thread_id=thread.id, run_id=run.id)
                                break
                            
                            tool_outputs = []
                            for tool_call in tool_calls:
                                if isinstance(tool_call, RequiredComputerUseToolCall):
                                    try:
                                        action = tool_call.computer_use_preview.action
                                        action_type = action.type
                                        
                                        # Log action
                                        action_info = {"type": action_type}
                                        if isinstance(action, ClickAction):
                                            action_info["x"] = action.x
                                            action_info["y"] = action.y
                                        elif isinstance(action, TypeAction):
                                            action_info["text"] = action.text
                                        result["actions"].append(action_info)
                                        
                                        # Execute action (async)
                                        if not isinstance(action, ComputerScreenshot):
                                            await self._execute_action(action)
                                        
                                        # Take screenshot (async)
                                        screenshot_path, screenshot_base64 = await self._take_screenshot()
                                        screenshot_url = f"data:image/png;base64,{screenshot_base64}"
                                        
                                        tool_outputs.append(
                                            ComputerToolOutput(
                                                tool_call_id=tool_call.id,
                                                output=ComputerScreenshot(image_url=screenshot_url)
                                            )
                                        )
                                    except Exception as e:
                                        print(f"Error executing action: {e}")
                            
                            if tool_outputs:
                                agents_client.runs.submit_tool_outputs(
                                    thread_id=thread.id,
                                    run_id=run.id,
                                    tool_outputs=tool_outputs
                                )
                    
                    if run.status == "failed":
                        raise Exception(f"Run failed: {run.last_error}")
                    
                    # Get response
                    response_message = agents_client.messages.get_last_message_by_role(
                        thread_id=thread.id,
                        role=MessageRole.AGENT
                    )
                    
                    if response_message:
                        for text_message in response_message.text_messages:
                            result["result"] = text_message.text.value
                    
                finally:
                    agents_client.delete_agent(agent.id)
            
            result["screenshots"] = self.screenshots
            
        finally:
            await self._stop_browser()
        
        return result
