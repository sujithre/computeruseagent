"""
Azure AI Foundry Computer Use Agent Sample

This sample demonstrates how to use the Computer Use tool with Azure AI Foundry Agents.
The agent can perform computer automation tasks like clicking, typing, taking screenshots,
and interacting with the desktop environment.

Prerequisites:
- Azure AI Foundry project with Computer Use tool enabled
- Computer Use model deployment configured
- Required packages: azure-ai-agents, azure-ai-projects, azure-identity, python-dotenv, playwright
- Run 'playwright install' to install browser binaries
"""
import os
import time
import base64
from typing import List, Optional
import config
from azure.ai.agents import AgentsClient
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

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not installed. Install with: pip install playwright && playwright install")


def image_to_base64(image_path: str) -> str:
    """
    Convert an image file to a Base64-encoded string.

    :param image_path: The path to the image file (e.g. 'image_file.png')
    :return: A Base64-encoded string representing the image.
    :raises FileNotFoundError: If the provided file path does not exist.
    :raises OSError: If there's an error reading the file.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"File not found at: {image_path}")

    try:
        with open(image_path, "rb") as image_file:
            file_data = image_file.read()
        return base64.b64encode(file_data).decode("utf-8")
    except Exception as exc:
        raise OSError(f"Error reading file '{image_path}'") from exc


def create_computer_use_agent(display_width: int = 1920, display_height: int = 1080):
    """
    Create and configure the Computer Use agent.
    
    Args:
        display_width: Width of the display/viewport in pixels.
        display_height: Height of the display/viewport in pixels.
    """
    # Initialize the agents client with endpoint from environment
    agents_client = AgentsClient(
        endpoint=config.PROJECT_ENDPOINT,
        credential=DefaultAzureCredential()
    )

    # Get environment type (windows, mac, linux, browser)
    environment = config.COMPUTER_USE_ENVIRONMENT

    # Initialize Computer Use tool with display dimensions
    computer_use = ComputerUseTool(
        display_width=display_width,
        display_height=display_height,
        environment=environment
    )

    return agents_client, computer_use


def run_computer_use_task(
    user_message: str,
    initial_screenshot_path: str,
    screenshot_callback=None,
    action_callback=None,
    display_width: int = 1920,
    display_height: int = 1080
):
    """
    Run a computer use task with the given user message and initial screenshot.
    
    Args:
        user_message: The task description for the computer use agent.
        initial_screenshot_path: Path to the initial screenshot of the screen state.
        screenshot_callback: Optional callback function to capture new screenshots.
                           Should return the path to a new screenshot.
        action_callback: Optional callback function to execute actions.
                        Receives the action object and should perform the action.
        display_width: Width of the display in pixels.
        display_height: Height of the display in pixels.
    """
    agents_client, computer_use = create_computer_use_agent(display_width, display_height)

    with agents_client:

        # Create a new Agent that has the Computer Use tool attached
        agent = agents_client.create_agent(
            model=config.COMPUTER_USE_MODEL_DEPLOYMENT_NAME,
            name="computer-use-agent",
            instructions="""
                You are a computer automation assistant.
                Use the computer_use_preview tool to interact with the screen when needed.
                Analyze screenshots carefully before taking actions.
                Be precise with click coordinates and typing actions.
            """,
            tools=computer_use.definitions,
        )
        print(f"Created agent, ID: {agent.id}")

        # Create thread for communication
        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Prepare initial message with screenshot
        image_base64 = image_to_base64(initial_screenshot_path)
        img_url = f"data:image/jpeg;base64,{image_base64}"
        url_param = MessageImageUrlParam(url=img_url, detail="high")
        
        content_blocks: List[MessageInputContentBlock] = [
            MessageInputTextBlock(text=user_message),
            MessageInputImageUrlBlock(image_url=url_param),
        ]

        # Create message to thread
        message = agents_client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=content_blocks
        )
        print(f"Created message, ID: {message.id}")

        # Create initial run
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        print(f"Created run, ID: {run.id}")

        # Process the run loop
        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)

            if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
                print("Run requires action:")
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                
                if not tool_calls:
                    print("No tool calls provided - cancelling run")
                    agents_client.runs.cancel(thread_id=thread.id, run_id=run.id)
                    break

                tool_outputs = []
                for tool_call in tool_calls:
                    if isinstance(tool_call, RequiredComputerUseToolCall):
                        print(tool_call)
                        try:
                            action = tool_call.computer_use_preview.action
                            output = execute_action(
                                action,
                                action_callback=action_callback,
                                screenshot_callback=screenshot_callback
                            )
                            tool_outputs.append(
                                ComputerToolOutput(tool_call_id=tool_call.id, output=output)
                            )
                        except Exception as e:
                            print(f"Error executing tool_call {tool_call.id}: {e}")

                print(f"Tool outputs: {tool_outputs}")
                if tool_outputs:
                    agents_client.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )

            print(f"Current run status: {run.status}")

        print(f"Run completed with status: {run.status}")
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Print run steps
        print_run_steps(agents_client, thread.id, run.id)

        # Print the Agent's response
        print_agent_response(agents_client, thread.id)

        # Delete the agent once the run is finished
        agents_client.delete_agent(agent.id)
        print("Deleted agent")


def execute_action(action, action_callback=None, screenshot_callback=None):
    """
    Execute a computer use action and return the result screenshot.
    
    Args:
        action: The action to execute (TypeAction, ClickAction, etc.)
        action_callback: Optional callback to execute the action in your environment.
        screenshot_callback: Optional callback to capture a screenshot after action.
    
    Returns:
        ComputerScreenshot with the result image.
    """
    action_type = action.type
    print(f"Executing computer use action: {action_type}")

    if isinstance(action, TypeAction):
        print(f"  Text to type: {action.text}")
        if action_callback:
            action_callback(action)
    
    elif isinstance(action, ClickAction):
        print(f"  Click at: ({action.x}, {action.y}), button: {getattr(action, 'button', 'left')}")
        if action_callback:
            action_callback(action)
    
    elif isinstance(action, ScrollAction):
        print(f"  Scroll: ({action.x}, {action.y}), delta: ({action.scroll_x}, {action.scroll_y})")
        if action_callback:
            action_callback(action)
    
    elif isinstance(action, ComputerScreenshot):
        print("  Screenshot requested")
    
    else:
        print(f"  Unknown action type: {action_type}")

    # Capture new screenshot after action
    if screenshot_callback:
        new_screenshot_path = screenshot_callback()
        result_image_base64 = image_to_base64(new_screenshot_path)
    else:
        # If no callback provided, use a placeholder (in real usage, implement proper screenshot)
        print("  Warning: No screenshot callback provided. Using empty response.")
        result_image_base64 = ""

    result_img_url = f"data:image/jpeg;base64,{result_image_base64}"
    return ComputerScreenshot(image_url=result_img_url)


def print_run_steps(agents_client, thread_id: str, run_id: str):
    """Print detailed information about each run step."""
    run_steps = agents_client.run_steps.list(thread_id=thread_id, run_id=run_id)

    for step in run_steps:
        print(f"Step {step.id} status: {step.status}")

        if isinstance(step.step_details, RunStepToolCallDetails):
            print("  Tool calls:")
            tool_calls = step.step_details.tool_calls

            for call in tool_calls:
                print(f"    Tool call ID: {call.id}")
                print(f"    Tool call type: {call.type}")

                if isinstance(call, RunStepComputerUseToolCall):
                    details = call.computer_use_preview
                    print(f"    Computer use action type: {details.action.type}")

                print()  # extra newline between tool calls

        print()  # extra newline between run steps


def print_agent_response(agents_client, thread_id: str):
    """Print the agent's response message."""
    response_message = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT
    )

    if response_message:
        for text_message in response_message.text_messages:
            print(f"Agent response: {text_message.text.value}")


class PlaywrightEnvironment:
    """Playwright-based browser environment for Computer Use agent."""
    
    def __init__(self, width: int = 1920, height: int = 1080, headless: bool = False):
        """
        Initialize the Playwright environment.
        
        Args:
            width: Browser viewport width.
            height: Browser viewport height.
            headless: Run browser in headless mode (no visible window).
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
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page(viewport={"width": self.width, "height": self.height})
        
        if url:
            self.page.goto(url, timeout=60000)
            # Use "load" instead of "networkidle" - some sites have continuous network activity
            try:
                self.page.wait_for_load_state("load", timeout=30000)
            except Exception:
                pass  # Continue even if timeout - page may still be usable
            time.sleep(2)  # Give page a moment to render
        
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
        if isinstance(action, ClickAction):
            button = getattr(action, 'button', 'left')
            if hasattr(button, 'value'):
                button = button.value
            self.page.mouse.click(action.x, action.y, button=button)
            time.sleep(0.5)  # Wait for any animations/navigation
        
        elif isinstance(action, TypeAction):
            self.page.keyboard.type(action.text)
            time.sleep(0.3)
        
        elif isinstance(action, ScrollAction):
            self.page.mouse.move(action.x, action.y)
            self.page.mouse.wheel(action.scroll_x, action.scroll_y)
            time.sleep(0.3)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def run_with_playwright(
    task: str,
    start_url: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    headless: bool = False
):
    """
    Run a computer use task with Playwright browser automation.
    
    Args:
        task: The task description for the agent.
        start_url: Optional URL to navigate to before starting.
        width: Browser viewport width.
        height: Browser viewport height.
        headless: Run browser in headless mode.
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
            display_height=height
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
        "--screenshot", "-s",
        type=str,
        help="Path to the initial screenshot (for manual mode without Playwright)"
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        default="Describe what you see on the screen.",
        help="The task for the agent to perform"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="URL to navigate to (enables Playwright mode)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Display/viewport width in pixels (default: 1280)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="Display/viewport height in pixels (default: 800)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)"
    )
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Use Playwright browser automation"
    )
    args = parser.parse_args()

    # If URL provided or --playwright flag, use Playwright mode
    if args.url or args.playwright:
        run_with_playwright(
            task=args.task,
            start_url=args.url,
            width=args.width,
            height=args.height,
            headless=args.headless
        )
    else:
        # Manual mode with screenshot
        if args.screenshot:
            screenshot_path = args.screenshot
        else:
            screenshot_path = capture_screen()
            if not screenshot_path:
                print("Could not capture screenshot. Please provide one with --screenshot or use --playwright mode")
                return

        if not os.path.exists(screenshot_path):
            print(f"Screenshot not found at: {screenshot_path}")
            return

        print(f"Using screenshot: {screenshot_path}")
        print(f"Task: {args.task}")
        
        run_computer_use_task(
            user_message=args.task,
            initial_screenshot_path=screenshot_path,
            display_width=args.width,
            display_height=args.height,
        )


def capture_screen():
    """Capture a screenshot of the current screen."""
    try:
        from PIL import ImageGrab
        
        # Create assets folder if it doesn't exist
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        screenshot_path = os.path.join(assets_dir, "screenshot.png")
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
        print(f"Captured screenshot: {screenshot_path}")
        return screenshot_path
    except ImportError:
        print("PIL not installed. Install with: pip install Pillow")
        return None
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None


if __name__ == "__main__":
    main()
