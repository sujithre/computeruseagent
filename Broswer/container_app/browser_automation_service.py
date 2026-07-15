"""
Browser Automation Service

Uses Azure's managed Playwright Workspaces via the BrowserAutomationTool.
No local browser or screenshots - everything runs in Azure's managed environment.
"""
import os
from typing import Optional, Dict, Any
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    MessageRole,
    RunStepToolCallDetails,
    BrowserAutomationTool,
    RunStepBrowserAutomationToolCall,
)
from azure.identity import DefaultAzureCredential


class BrowserAutomationService:
    """Service for running browser automation tasks via Azure managed Playwright."""
    
    def __init__(self, model_deployment_name: Optional[str] = None):
        """
        Initialize the Browser Automation service.
        
        Args:
            model_deployment_name: Optional override for the model deployment name.
        """
        self.project_endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.connection_name = os.environ.get("AZURE_PLAYWRIGHT_CONNECTION_NAME")
        self.model_name = model_deployment_name or os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")
        
        if not self.project_endpoint:
            raise ValueError("PROJECT_ENDPOINT environment variable is required")
        if not self.connection_name:
            raise ValueError("AZURE_PLAYWRIGHT_CONNECTION_NAME environment variable is required")
    
    def run_task(self, task: str) -> Dict[str, Any]:
        """
        Run a browser automation task.
        
        Args:
            task: The task description for the browser automation agent.
            
        Returns:
            Dictionary containing the result and any citations.
        """
        project_client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=DefaultAzureCredential()
        )
        
        browser_automation = BrowserAutomationTool(
            connection_id=self.connection_name
        )
        
        result = {
            "response": None,
            "citations": [],
            "steps": []
        }
        
        with project_client:
            agents_client = project_client.agents
            
            # Create agent
            agent = agents_client.create_agent(
                model=self.model_name,
                name="browser-automation-agent",
                instructions="""
                    You are an Agent helping with browser automation tasks. 
                    You can answer questions, provide information, and assist with various tasks 
                    related to web browsing using the Browser Automation tool available to you.
                    Be thorough and provide detailed results.
                """,
                tools=browser_automation.definitions,
            )
            
            try:
                # Create thread and message
                thread = agents_client.threads.create()
                agents_client.messages.create(
                    thread_id=thread.id,
                    role=MessageRole.USER,
                    content=task,
                )
                
                # Run the agent
                run = agents_client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent.id
                )
                
                if run.status == "failed":
                    raise Exception(f"Run failed: {run.last_error}")
                
                # Collect run steps
                run_steps = agents_client.run_steps.list(thread_id=thread.id, run_id=run.id)
                for step in run_steps:
                    if isinstance(step.step_details, RunStepToolCallDetails):
                        for call in step.step_details.tool_calls:
                            if isinstance(call, RunStepBrowserAutomationToolCall):
                                step_info = {
                                    "input": call.browser_automation.input,
                                    "output": call.browser_automation.output,
                                    "steps": []
                                }
                                for tool_step in call.browser_automation.steps:
                                    step_info["steps"].append({
                                        "last_step_result": tool_step.last_step_result,
                                        "current_state": tool_step.current_state,
                                        "next_step": tool_step.next_step
                                    })
                                result["steps"].append(step_info)
                
                # Get response
                response_message = agents_client.messages.get_last_message_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT
                )
                
                if response_message:
                    for text_message in response_message.text_messages:
                        result["response"] = text_message.text.value
                    for annotation in response_message.url_citation_annotations:
                        result["citations"].append({
                            "title": annotation.url_citation.title,
                            "url": annotation.url_citation.url
                        })
                
            finally:
                # Cleanup
                agents_client.delete_agent(agent.id)
        
        return result
