"""
Computer Use Service

Drives a headless Playwright browser with the Azure AI Foundry Computer Use tool
via the Responses API. Screenshots are saved to Azure Blob Storage using Managed Identity.
"""
import os
import io
import time
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from playwright.async_api import async_playwright, Page, Browser

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    BLOB_STORAGE_AVAILABLE = True
except ImportError:
    BLOB_STORAGE_AVAILABLE = False


AGENT_INSTRUCTIONS = """
You are a computer automation assistant.
Use the computer_use_preview tool to interact with the screen when needed.
Analyze screenshots carefully before taking actions.
Be precise with click coordinates and typing actions.
Be direct and efficient. When you complete a task, describe what you accomplished.

Never claim a step succeeded unless the latest screenshot visibly shows it.
If the screen looks unchanged after a click, the click missed: re-examine the
screenshot, aim at the centre of the target element, and click again.
"""

# The model emits these names; Playwright expects its own spelling.
_KEY_ALIASES = {
    "ENTER": "Enter",
    "RETURN": "Enter",
    "TAB": "Tab",
    "ESC": "Escape",
    "ESCAPE": "Escape",
    "SPACE": " ",
    "BACKSPACE": "Backspace",
    "DELETE": "Delete",
    "ARROWUP": "ArrowUp",
    "ARROWDOWN": "ArrowDown",
    "ARROWLEFT": "ArrowLeft",
    "ARROWRIGHT": "ArrowRight",
    "CTRL": "Control",
    "CMD": "Meta",
}


class ComputerUseService:
    """Service for running computer use tasks with Playwright and screenshot capture."""

    def __init__(
        self,
        width: int = 1280,
        height: int = 800,
        save_screenshots: bool = True,
        task_id: Optional[str] = None,
        max_steps: int = 20,
        ignore_https_errors: Optional[bool] = None
    ):
        """
        Initialize the Computer Use service.

        Args:
            width: Browser viewport width.
            height: Browser viewport height.
            save_screenshots: Whether to save screenshots.
            task_id: Unique task ID for organizing screenshots.
            max_steps: Maximum agent action iterations before the run is stopped.
            ignore_https_errors: Accept certificates that do not chain to a public CA.
        """
        self.width = width
        self.height = height
        self.save_screenshots = save_screenshots
        self.task_id = task_id or str(int(time.time()))
        self.max_steps = max_steps
        if ignore_https_errors is None:
            ignore_https_errors = os.environ.get("IGNORE_HTTPS_ERRORS", "").lower() == "true"
        self.ignore_https_errors = ignore_https_errors

        self.project_endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.model_name = os.environ.get("COMPUTER_USE_MODEL_DEPLOYMENT_NAME",
                                         os.environ.get("MODEL_DEPLOYMENT_NAME", "computer-use-preview"))
        self.environment = os.environ.get("COMPUTER_USE_ENVIRONMENT", "browser")

        if not self.project_endpoint:
            raise ValueError("PROJECT_ENDPOINT environment variable is required")

        # Azure Blob Storage configuration
        self.storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "screenshots")
        self.use_blob_storage = bool(self.storage_account_name) and BLOB_STORAGE_AVAILABLE

        self.blob_service_client = None
        self.container_client = None
        if self.use_blob_storage:
            self._init_blob_storage()

        self.screenshots: List[str] = []
        self.screenshot_dir = os.path.join("/tmp", "screenshots", self.task_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def _init_blob_storage(self):
        """Initialize Azure Blob Storage client with Managed Identity."""
        try:
            credential = DefaultAzureCredential()
            account_url = f"https://{self.storage_account_name}.blob.core.windows.net"

            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)

            try:
                self.container_client.get_container_properties()
            except Exception:
                self.container_client.create_container()

            print(f"Blob storage initialized: {account_url}/{self.container_name}")
        except Exception as e:
            print(f"Warning: Failed to initialize blob storage: {e}")
            self.use_blob_storage = False

    def _proxy_settings(self) -> Optional[Dict[str, Any]]:
        """Build Playwright proxy config; the browser does not inherit container proxy vars."""
        server = (
            os.environ.get("BROWSER_PROXY_SERVER")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )
        if not server:
            return None

        proxy: Dict[str, Any] = {"server": server}
        bypass = os.environ.get("BROWSER_PROXY_BYPASS") or os.environ.get("NO_PROXY")
        if bypass:
            # Playwright expects ".domain.com" rather than the "*.domain.com" used by NO_PROXY.
            entries = [e.strip().lstrip("*") for e in bypass.split(",") if e.strip()]
            proxy["bypass"] = ",".join(entries)
        return proxy

    async def _start_browser(self, url: Optional[str] = None):
        """Start the Playwright browser (async)."""
        self.playwright = await async_playwright().start()
        print(f"Starting browser with ignore_https_errors={self.ignore_https_errors}")
        launch_args: Dict[str, Any] = {"headless": True}  # Always headless in container
        if self.ignore_https_errors:
            # Context-level ignoreHTTPSErrors is overridden by HSTS; the launch flag is not.
            launch_args["args"] = ["--ignore-certificate-errors"]
        proxy = self._proxy_settings()
        if proxy:
            launch_args["proxy"] = proxy
            print(f"Browser using proxy: {proxy['server']}")

        self.browser = await self.playwright.chromium.launch(**launch_args)
        context = await self.browser.new_context(
            viewport={"width": self.width, "height": self.height},
            ignore_https_errors=self.ignore_https_errors,
        )
        self.page = await context.new_page()

        if url:
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")

    async def _stop_browser(self):
        """Stop the Playwright browser (async)."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _first_visible(self, scope, selectors: List[str]):
        """Return the first selector in the list that resolves to a visible element."""
        for selector in selectors:
            if not selector:
                continue
            try:
                locator = scope.locator(selector).first
                await locator.wait_for(state="visible", timeout=5000)
                return locator
            except Exception:
                continue
        return None

    async def _find_in_frames(self, selectors: List[str]):
        """Search the main frame and every child frame for the first visible match."""
        for scope in [self.page] + list(self.page.frames):
            found = await self._first_visible(scope, selectors)
            if found is not None:
                return found
        return None

    async def _type_into(self, field, value: str):
        """Click, clear, and type a value with real keystrokes."""
        await field.click()
        try:
            await field.fill("")
        except Exception:
            pass
        await field.type(value, delay=60)

    async def _login(self, credentials: Dict[str, Any]):
        """Sign in with Playwright so credentials never reach the model or screenshots."""
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            raise ValueError("Login requires both a username and a password")

        await self.page.wait_for_load_state("domcontentloaded")

        user_field = await self._find_in_frames([
            credentials.get("username_selector"),
            "#userid",
            "input[name='userid']",
            "input[name='username']",
            "input[type='email']",
            "input[type='text']:visible",
        ])
        pass_field = await self._find_in_frames([
            credentials.get("password_selector"),
            "#password",
            "input[name='password']",
            "input[type='password']:visible",
        ])

        if user_field is None or pass_field is None:
            raise RuntimeError("Could not locate the sign in fields on the page")

        await self._type_into(user_field, username)
        await self._type_into(pass_field, password)

        submit = await self._find_in_frames([
            credentials.get("submit_selector"),
            "#btnActiveLogin",
            "button[type='submit']",
            "input[type='submit']",
        ])
        if submit is not None:
            await submit.click()
        else:
            await pass_field.press("Enter")

        try:
            await self.page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        print(f"Signed in. Current page: {self.page.url}")

    def _compress_to_base64(self, image_path: str, quality: int = 70, max_base64_kb: int = 45) -> str:
        """Encode a screenshot small enough for the Responses API to accept on follow-up turns."""
        if not PIL_AVAILABLE:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)

            current_quality = quality
            while True:
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                if len(encoded) / 1024 <= max_base64_kb or current_quality <= 15:
                    return encoded
                current_quality = max(15, current_quality - 15)

    async def _take_screenshot(self) -> tuple:
        """Take a screenshot and return the path and compressed base64 data (async)."""
        os.makedirs(self.screenshot_dir, exist_ok=True)

        timestamp = int(time.time() * 1000)
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)

        await self.page.screenshot(path=filepath)
        screenshot_base64 = self._compress_to_base64(filepath)

        if self.save_screenshots:
            if self.use_blob_storage:
                self.screenshots.append(self._upload_to_blob(filepath, filename))
            else:
                self.screenshots.append(filepath)

        return filepath, screenshot_base64

    def _upload_to_blob(self, filepath: str, filename: str) -> str:
        """Upload screenshot to Azure Blob Storage using Managed Identity."""
        try:
            blob_name = f"{self.task_id}/{filename}"
            blob_client = self.container_client.get_blob_client(blob_name)

            with open(filepath, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            try:
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
                blob_url = (f"https://{self.storage_account_name}.blob.core.windows.net/"
                            f"{self.container_name}/{blob_name}?{sas_token}")
            except Exception as e:
                print(f"Warning: Could not generate SAS token: {e}")
                blob_url = (f"https://{self.storage_account_name}.blob.core.windows.net/"
                            f"{self.container_name}/{blob_name}")

            print(f"  Uploaded screenshot to blob: {blob_name}")

            try:
                os.remove(filepath)
            except Exception:
                pass

            return blob_url

        except Exception as e:
            print(f"Warning: Failed to upload to blob storage: {e}")
            return filepath

    async def _execute_action(self, action):
        """Execute a single computer use action in the browser (async)."""
        action_type = getattr(action, "type", None)

        if action_type == "click":
            button = getattr(action, "button", "left")
            if hasattr(button, "value"):
                button = button.value
            await self.page.mouse.click(action.x, action.y, button=button or "left")
            await asyncio.sleep(0.5)

        elif action_type == "double_click":
            await self.page.mouse.dblclick(action.x, action.y)
            await asyncio.sleep(0.5)

        elif action_type == "move":
            await self.page.mouse.move(action.x, action.y)

        elif action_type == "type":
            await self.page.keyboard.type(action.text)
            await asyncio.sleep(0.3)

        elif action_type in ("key", "keypress"):
            keys = getattr(action, "keys", None) or [getattr(action, "key", "")]
            for key in keys:
                await self.page.keyboard.press(_KEY_ALIASES.get(str(key).upper(), str(key)))
                await asyncio.sleep(0.2)

        elif action_type == "scroll":
            await self.page.mouse.move(action.x, action.y)
            await self.page.mouse.wheel(getattr(action, "scroll_x", 0), getattr(action, "scroll_y", 0))
            await asyncio.sleep(0.3)

        elif action_type == "wait":
            await asyncio.sleep(1)

        elif action_type == "screenshot":
            pass

        else:
            print(f"  Unknown action type: {action_type}")

    async def run_task(
        self,
        task: str,
        start_url: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a computer use task (async).

        Args:
            task: The task description for the computer use agent.
            start_url: Optional URL to navigate to before starting.
            credentials: Optional sign-in details applied before the agent takes over.

        Returns:
            Dictionary containing the result and screenshot paths.
        """
        result: Dict[str, Any] = {"result": None, "screenshots": [], "actions": []}

        try:
            await self._start_browser(url=start_url)

            if credentials:
                await self._login(credentials)

            _, screenshot_base64 = await self._take_screenshot()
            image_url = f"data:image/jpeg;base64,{screenshot_base64}"

            project = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=DefaultAzureCredential(),
            )
            openai = project.get_openai_client()

            tool_payload = {
                "type": "computer_use_preview",
                "display_width": self.width,
                "display_height": self.height,
                "environment": self.environment,
            }
            base_kwargs = {"model": self.model_name, "tools": [tool_payload]}
            # tool_choice "auto" makes this deployment narrate actions instead of
            # emitting computer_call items, so force tool use to drive the loop.
            forced_kwargs = {**base_kwargs, "tool_choice": "required"}

            def create_response(**kwargs):
                return openai.responses.create(truncation="auto", **kwargs)

            response = await asyncio.to_thread(
                create_response,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"{AGENT_INSTRUCTIONS}\n\n{task}"},
                        {"type": "input_image", "image_url": image_url, "detail": "high"},
                    ],
                }],
                **forced_kwargs,
            )

            iteration = 0
            last_signature = None
            repeat_count = 0
            pending_output = None

            while True:
                iteration += 1
                computer_calls = [item for item in response.output if item.type == "computer_call"]

                if not computer_calls:
                    break

                computer_call = computer_calls[0]
                actions = getattr(computer_call, "actions", None) or [computer_call.action]
                call_id = computer_call.call_id

                safety_checks = getattr(computer_call, "pending_safety_checks", None)

                for action in actions:
                    info = {"type": getattr(action, "type", None)}
                    for attr in ("x", "y", "text"):
                        if hasattr(action, attr):
                            info[attr] = getattr(action, attr)
                    result["actions"].append(info)
                    await self._execute_action(action)

                signature = str([(getattr(a, "type", None), getattr(a, "x", None),
                                  getattr(a, "y", None), getattr(a, "text", None)) for a in actions])
                if signature == last_signature:
                    repeat_count += 1
                else:
                    repeat_count = 0
                    last_signature = signature

                _, screenshot_base64 = await self._take_screenshot()
                new_image_url = f"data:image/jpeg;base64,{screenshot_base64}"

                computer_call_output: Dict[str, Any] = {
                    "call_id": call_id,
                    "type": "computer_call_output",
                    "output": {"type": "computer_screenshot", "image_url": new_image_url},
                }
                if safety_checks:
                    computer_call_output["acknowledged_safety_checks"] = [
                        {"id": c.id, "code": c.code, "message": c.message} for c in safety_checks
                    ]

                if repeat_count >= 3 or iteration >= self.max_steps:
                    pending_output = computer_call_output
                    break

                # Forced tool use means the model can never signal completion, so only
                # offer it the chance to stop once it is idling.
                idling = all(getattr(a, "type", None) in ("wait", "screenshot") for a in actions)

                if idling:
                    response = await asyncio.to_thread(
                        create_response,
                        previous_response_id=response.id,
                        input=[
                            computer_call_output,
                            {"role": "user", "content": [{
                                "type": "input_text",
                                "text": "Reply with exactly TASK COMPLETE only if every step of "
                                        "the task has been carried out and you can see the result "
                                        "on screen. Otherwise carry out the next action.",
                            }]},
                        ],
                        **base_kwargs,
                    )
                    pending_output = None

                    if not [i for i in response.output if i.type == "computer_call"]:
                        text = " ".join(
                            content.text
                            for item in response.output if item.type == "message"
                            for content in item.content if hasattr(content, "text")
                        )
                        if "TASK COMPLETE" in text.upper():
                            break
                        response = await asyncio.to_thread(
                            create_response,
                            previous_response_id=response.id,
                            input=[{"role": "user", "content": [
                                {"type": "input_text", "text": "Carry out the next action now."}
                            ]}],
                            **forced_kwargs,
                        )
                else:
                    response = await asyncio.to_thread(
                        create_response,
                        previous_response_id=response.id,
                        input=[computer_call_output],
                        **forced_kwargs,
                    )
                    pending_output = None

            # Closing summary without forced tool use, so the model answers in text.
            try:
                summary_input: List[Any] = []
                if pending_output:
                    summary_input.append(pending_output)
                summary_input.append({"role": "user", "content": [{
                    "type": "input_text",
                    "text": "Stop interacting with the screen. Describe what you "
                            "accomplished and what is currently displayed.",
                }]})
                summary = await asyncio.to_thread(
                    create_response,
                    previous_response_id=response.id,
                    input=summary_input,
                    **base_kwargs,
                )
                result["result"] = " ".join(
                    content.text
                    for item in summary.output if item.type == "message"
                    for content in item.content if hasattr(content, "text")
                )
            except Exception as exc:
                print(f"Could not get summary: {exc}")
                result["result"] = " ".join(
                    content.text
                    for item in response.output if item.type == "message"
                    for content in item.content if hasattr(content, "text")
                )

            result["screenshots"] = self.screenshots

        finally:
            await self._stop_browser()

        return result
