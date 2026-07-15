"""
Azure AI Foundry Computer Use Agent Sample

This sample demonstrates how to use the Computer Use tool with Azure AI Foundry Agents.
The agent can perform computer automation tasks like clicking, typing, taking screenshots,
and interacting with the desktop environment.

Prerequisites:
- Azure AI Foundry project with Computer Use tool enabled
- Computer Use model deployment (computer-use-preview)
- Required packages: azure-ai-projects, azure-identity, python-dotenv, playwright
- Run 'playwright install' to install browser binaries
"""
import os
import time
import base64
import io
from typing import Optional
import config
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, ComputerUsePreviewTool
from azure.identity import AzureCliCredential, DefaultAzureCredential


def _get_credential():
    """Return an Azure credential.

    Prefer the Azure CLI credential (works after `az login`) because
    DefaultAzureCredential can fail to invoke the CLI as a subprocess on
    some Windows/venv setups. Fall back to DefaultAzureCredential otherwise.
    """
    try:
        cred = AzureCliCredential()
        # Validate that the CLI login actually works.
        cred.get_token("https://cognitiveservices.azure.com/.default")
        return cred
    except Exception:
        return DefaultAzureCredential()

# PIL for image compression
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Install with: pip install Pillow")

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not installed. Install with: pip install playwright && playwright install")


def image_to_base64(image_path: str, target_width: int = 800, target_height: int = 600, quality: int = 25) -> str:
    """
    Convert an image file to a Base64-encoded string, resized to exact dimensions.
    
    Args:
        image_path: Path to the image file
        target_width: Target width to resize to
        target_height: Target height to resize to  
        quality: JPEG quality (1-100, lower = smaller file)
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"File not found at: {image_path}")

    if PIL_AVAILABLE:
        # Open and resize image to exact target dimensions
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize to exact target dimensions
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Save to bytes as JPEG with compression
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            file_data = buffer.getvalue()
            base64_str = base64.b64encode(file_data).decode("utf-8")
            print(f"    Image: {len(file_data) / 1024:.1f} KB, base64: {len(base64_str) / 1024:.1f} KB")
        return base64_str
    else:
        # Fallback: read file directly (no compression)
        with open(image_path, "rb") as image_file:
            file_data = image_file.read()
        return base64.b64encode(file_data).decode("utf-8")


def execute_action(action, action_callback=None):
    """
    Execute a computer use action.
    
    Args:
        action: The action object from the response
        action_callback: Optional callback to execute the action in your environment.
    """
    action_type = action.type
    print(f"  Action type: {action_type}")

    if action_type == "type":
        print(f"  Typing text: {action.text}")
        if action_callback:
            action_callback(action)
    
    elif action_type == "click":
        button = getattr(action, 'button', 'left')
        print(f"  Click at: ({action.x}, {action.y}), button: {button}")
        if action_callback:
            action_callback(action)
    
    elif action_type == "scroll":
        print(f"  Scroll at: ({action.x}, {action.y}), delta: ({action.scroll_x}, {action.scroll_y})")
        if action_callback:
            action_callback(action)
    
    elif action_type == "screenshot":
        print("  Screenshot requested")
    
    elif action_type == "wait":
        print("  Wait requested")
        time.sleep(1)
    
    elif action_type == "key":
        print(f"  Key press: {action.key}")
        if action_callback:
            action_callback(action)
    
    else:
        print(f"  Unknown action type: {action_type}")


def run_computer_use_task(
    user_message: str,
    initial_screenshot_path: str,
    screenshot_callback=None,
    action_callback=None,
    display_width: int = 800,
    display_height: int = 600,
    max_iterations: int = 20
):
    """
    Run a computer use task using the Responses API pattern from the documentation.
    
    Args:
        user_message: The task description for the computer use agent.
        initial_screenshot_path: Path to the initial screenshot of the screen state.
        screenshot_callback: Optional callback function to capture new screenshots.
        action_callback: Optional callback function to execute actions.
        display_width: Width of the display in pixels.
        display_height: Height of the display in pixels.
        max_iterations: Maximum number of action iterations.
    """
    # Initialize the project client
    project = AIProjectClient(
        endpoint=config.PROJECT_ENDPOINT,
        credential=_get_credential(),
    )

    # Get environment type (windows, mac, linux, browser)
    environment = config.COMPUTER_USE_ENVIRONMENT

    # Initialize Computer Use tool with display dimensions
    computer_use_tool = ComputerUsePreviewTool(
        display_width=display_width,
        display_height=display_height,
        environment=environment
    )

    # Create a versioned agent with the Computer Use tool
    agent = project.agents.create_version(
        agent_name="ComputerUseAgent",
        definition=PromptAgentDefinition(
            model=config.COMPUTER_USE_MODEL_DEPLOYMENT_NAME,
            instructions="""
            You are a computer automation assistant.
            Use the computer_use_preview tool to interact with the screen when needed.
            Analyze screenshots carefully before taking actions.
            Be precise with click coordinates and typing actions.
            Be direct and efficient. When you complete a task, describe what you accomplished.
            """,
            tools=[computer_use_tool],
        ),
        description="Computer automation agent with screen interaction capabilities.",
    )
    print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

    # Get OpenAI client for Responses API
    openai = project.get_openai_client()

    # Prepare initial screenshot
    image_base64 = image_to_base64(initial_screenshot_path, target_width=display_width, target_height=display_height)
    image_url = f"data:image/jpeg;base64,{image_base64}"

    # Initial request with screenshot
    response = openai.responses.create(
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_message,
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "high",
                    },
                ],
            }
        ],
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        truncation="auto",
    )

    print(f"Initial response received (ID: {response.id})")

    # Process iterations
    iteration = 0
    while True:
        if iteration >= max_iterations:
            print(f"\nReached maximum iterations ({max_iterations}). Stopping.")
            break

        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Check for computer calls in the response
        computer_calls = [item for item in response.output if item.type == "computer_call"]

        if not computer_calls:
            # No more computer calls - print final output and break
            print("\nNo more computer calls. Final output:")
            for item in response.output:
                if item.type == "message":
                    for content in item.content:
                        if hasattr(content, 'text'):
                            print(f"  Agent: {content.text}")
            break

        # Process the first computer call
        computer_call = computer_calls[0]
        action = computer_call.action
        call_id = computer_call.call_id

        print(f"Processing computer call (ID: {call_id})")

        # Check for safety checks
        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
            print("  Safety checks pending:")
            for check in computer_call.pending_safety_checks:
                print(f"    - {check.code}: {check.message}")
            # For automation, we acknowledge safety checks automatically
            # In production, you should require user confirmation
            acknowledged_safety_checks = computer_call.pending_safety_checks
        else:
            acknowledged_safety_checks = None

        # Execute the action
        execute_action(action, action_callback=action_callback)

        # Take new screenshot after action
        if screenshot_callback:
            new_screenshot_path = screenshot_callback()
            new_image_base64 = image_to_base64(new_screenshot_path, target_width=display_width, target_height=display_height)
            new_image_url = f"data:image/jpeg;base64,{new_image_base64}"
        else:
            print("  Warning: No screenshot callback - using same screenshot")
            new_image_url = image_url

        # Build the input for next response
        computer_call_output = {
            "call_id": call_id,
            "type": "computer_call_output",
            "output": {
                "type": "computer_screenshot",
                "image_url": new_image_url,
            },
        }

        # Add acknowledged safety checks if present
        if acknowledged_safety_checks:
            computer_call_output["acknowledged_safety_checks"] = [
                {"id": check.id, "code": check.code, "message": check.message}
                for check in acknowledged_safety_checks
            ]

        # Send next request with updated screenshot
        response = openai.responses.create(
            previous_response_id=response.id,
            input=[computer_call_output],
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            truncation="auto",
        )

        print(f"Response received (ID: {response.id})")

    # Clean up - delete the agent version
    project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
    print("\nAgent deleted")


class PlaywrightEnvironment:
    """Playwright-based browser environment for Computer Use agent."""
    
    def __init__(self, width: int = 800, height: int = 600, headless: bool = False):
        """
        Initialize the Playwright environment.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install")
        
        self.width = width
        self.height = height
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), "assets")
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def start(self, url: Optional[str] = None):
        """Start the browser and optionally navigate to a URL."""
        self.playwright = sync_playwright().start()
        # Prefer an already-installed system browser (Chrome/Edge) so we don't
        # need to download Playwright's bundled Chromium. Falls back to the
        # bundled Chromium if no system channel is available.
        launch_error: Optional[Exception] = None
        for channel in ("chrome", "msedge", None):
            try:
                if channel:
                    self.browser = self.playwright.chromium.launch(
                        headless=self.headless, channel=channel
                    )
                else:
                    self.browser = self.playwright.chromium.launch(headless=self.headless)
                break
            except Exception as exc:  # noqa: BLE001 - try next channel
                launch_error = exc
                self.browser = None
        if self.browser is None:
            raise RuntimeError(
                "Could not launch a browser. Install Google Chrome/Edge, or run "
                "'playwright install chromium' when you have network access."
            ) from launch_error
        self.page = self.browser.new_page(viewport={"width": self.width, "height": self.height})
        
        if url:
            self.page.goto(url, timeout=60000)
            try:
                self.page.wait_for_load_state("load", timeout=30000)
            except Exception:
                pass
            time.sleep(2)
        
        return self
    
    def stop(self):
        """Close the browser and cleanup."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def take_screenshot(self) -> str:
        """Capture a screenshot of the current page."""
        screenshot_path = os.path.join(self.screenshot_dir, f"screenshot_{int(time.time())}.png")
        self.page.screenshot(path=screenshot_path)
        print(f"  Captured screenshot: {screenshot_path}")
        return screenshot_path
    
    def execute_action(self, action):
        """Execute a computer use action in the browser."""
        action_type = action.type
        
        if action_type == "click":
            button = getattr(action, 'button', 'left')
            if hasattr(button, 'value'):
                button = button.value
            self.page.mouse.click(action.x, action.y, button=button)
            time.sleep(0.5)
        
        elif action_type == "type":
            self.page.keyboard.type(action.text)
            time.sleep(0.3)
        
        elif action_type == "scroll":
            self.page.mouse.move(action.x, action.y)
            self.page.mouse.wheel(action.scroll_x, action.scroll_y)
            time.sleep(0.3)
        
        elif action_type == "key":
            # Handle special keys
            key = action.key
            self.page.keyboard.press(key)
            time.sleep(0.3)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def run_with_playwright(
    task: str,
    start_url: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    headless: bool = False,
    max_iterations: int = 20
):
    """
    Run a computer use task with Playwright browser automation.
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("Error: Playwright is not installed.")
        print("Install with: pip install playwright && playwright install")
        return
    
    env = PlaywrightEnvironment(width=width, height=height, headless=headless)
    
    try:
        env.start(url=start_url)
        print(f"Browser started. Viewport: {width}x{height}")
        if start_url:
            print(f"Navigated to: {start_url}")
        
        # Take initial screenshot
        initial_screenshot = env.take_screenshot()
        
        # Run the agent with Playwright callbacks
        run_computer_use_task(
            user_message=task,
            initial_screenshot_path=initial_screenshot,
            screenshot_callback=env.take_screenshot,
            action_callback=env.execute_action,
            display_width=width,
            display_height=height,
            max_iterations=max_iterations
        )
        
        print("\nTask completed. Press Enter to close the browser...")
        input()
        
    finally:
        env.stop()
        print("Browser closed.")


def main():
    """Main entry point with a sample computer use task."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Computer Use Agent")
    parser.add_argument(
        "--task", "-t",
        type=str,
        default="Describe what you see on the screen.",
        help="The task for the agent to perform"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="URL to navigate to"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=1920,
        help="Browser viewport width"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=1080,
        help="Browser viewport height"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=20,
        help="Maximum number of action iterations"
    )
    
    args = parser.parse_args()
    
    run_with_playwright(
        task=args.task,
        start_url=args.url,
        width=args.width,
        height=args.height,
        headless=args.headless,
        max_iterations=args.max_iterations
    )


if __name__ == "__main__":
    main()
