"""
Azure AI Foundry Browser Automation Agent Sample

This sample demonstrates how to use the Browser Automation tool with Azure AI Foundry Agents.
The agent can perform browser automation tasks like navigating websites, clicking elements,
and extracting information.

Prerequisites:
- Azure AI Foundry project with Browser Automation tool enabled
- Microsoft Playwright Workspaces connection configured
- Required packages: azure-ai-agents, azure-ai-projects, azure-identity, python-dotenv
"""
import config
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    MessageRole,
    RunStepToolCallDetails,
    BrowserAutomationTool,
    RunStepBrowserAutomationToolCall,
)
from azure.identity import DefaultAzureCredential


def create_browser_automation_agent():
    """Create and configure the Browser Automation agent."""
    
    # Initialize the project client with endpoint from environment
    project_client = AIProjectClient(
        endpoint=config.PROJECT_ENDPOINT, 
        credential=DefaultAzureCredential()
    )

    # Initialize Browser Automation tool with the connection name from environment
    browser_automation = BrowserAutomationTool(
        connection_id=config.AZURE_PLAYWRIGHT_CONNECTION_NAME
    )

    return project_client, browser_automation


def run_browser_automation_task(user_message: str):
    """
    Run a browser automation task with the given user message.
    
    Args:
        user_message: The task description for the browser automation agent.
    """
    project_client, browser_automation = create_browser_automation_agent()

    with project_client:
        agents_client = project_client.agents

        # Create a new Agent that has the Browser Automation tool attached
        agent = agents_client.create_agent(
            model=config.MODEL_DEPLOYMENT_NAME,
            name="browser-automation-agent",
            instructions="""
                You are an Agent helping with browser automation tasks. 
                You can answer questions, provide information, and assist with various tasks 
                related to web browsing using the Browser Automation tool available to you.
            """,
            tools=browser_automation.definitions,
        )
        print(f"Created agent, ID: {agent.id}")

        # Create thread for communication
        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Create message to thread
        message = agents_client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=user_message,
        )
        print(f"Created message, ID: {message.id}")

        # Create and process agent run in thread with tools
        print("Waiting for Agent run to complete. Please wait...")
        run = agents_client.runs.create_and_process(
            thread_id=thread.id, 
            agent_id=agent.id
        )
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Fetch run steps to get the details of the agent run
        print_run_steps(agents_client, thread.id, run.id)

        # Print the Agent's response message with optional citation
        print_agent_response(agents_client, thread.id)

        # Delete the agent once the run is finished
        # Comment out this line if you plan to reuse the agent later
        agents_client.delete_agent(agent.id)
        print("Deleted agent")


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

                if isinstance(call, RunStepBrowserAutomationToolCall):
                    print(f"    Browser automation input: {call.browser_automation.input}")
                    print(f"    Browser automation output: {call.browser_automation.output}")

                    print("    Steps:")
                    for tool_step in call.browser_automation.steps:
                        print(f"      Last step result: {tool_step.last_step_result}")
                        print(f"      Current state: {tool_step.current_state}")
                        print(f"      Next step: {tool_step.next_step}")
                        print()  # add an extra newline between tool steps

                print()  # add an extra newline between tool calls

        print()  # add an extra newline between run steps


def print_agent_response(agents_client, thread_id: str):
    """Print the agent's response message with any URL citations."""
    response_message = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id, 
        role=MessageRole.AGENT
    )
    
    if response_message:
        for text_message in response_message.text_messages:
            print(f"Agent response: {text_message.text.value}")
        for annotation in response_message.url_citation_annotations:
            print(f"URL Citation: [{annotation.url_citation.title}]({annotation.url_citation.url})")


def main():
    """Main entry point with a sample browser automation task."""
    
    # Example task: Get Microsoft stock price change
    sample_task = """
        Your goal is to report the percent of Microsoft year-to-date stock price change.
        To do that, go to the website finance.yahoo.com.
        At the top of the page, you will find a search bar.
        Enter the value 'MSFT', to get information about the Microsoft stock price.
        At the top of the resulting page you will see a default chart of Microsoft stock price.
        Click on 'YTD' at the top of that chart, and report the percent value that shows up just below it.
    """
    
    run_browser_automation_task(sample_task)


if __name__ == "__main__":
    main()
