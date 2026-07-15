# Azure AI Foundry Browser Automation Agent

This sample demonstrates how to use the Browser Automation tool with Azure AI Foundry Agents.

## Prerequisites

1. An Azure AI Foundry project with Browser Automation tool enabled
2. A Microsoft Playwright Workspaces connection configured in your project
3. Python 3.8 or later

## Setup

1. **Create and activate virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   
   Copy `.env.example` to `.env` and fill in your values:
   ```powershell
   cp .env.example .env
   ```

   Update the following variables in `.env`:
   
   | Variable | Description | Where to Find |
   |----------|-------------|---------------|
   | `PROJECT_ENDPOINT` | Your Azure AI Foundry project endpoint | Foundry portal > Project overview > Libraries > Foundry |
   | `AZURE_PLAYWRIGHT_CONNECTION_NAME` | Your Playwright connection name | Foundry portal > Management center > Connected resources |
   | `MODEL_DEPLOYMENT_NAME` | Your model deployment name (e.g., `gpt-4o`) | Foundry portal > Models + Endpoints |

## Usage

Run the sample:
```powershell
python browser_automation_agent.py
```

The sample will:
1. Create a Browser Automation agent
2. Send a task to get Microsoft's year-to-date stock price change from Yahoo Finance
3. Print the agent's step-by-step actions and final response
4. Clean up by deleting the agent

## Customizing the Task

Edit the `sample_task` variable in `browser_automation_agent.py` to change the browser automation task:

```python
sample_task = """
    Your goal is to [describe your task here].
    Navigate to [website].
    [Step-by-step instructions for the agent].
"""

run_browser_automation_task(sample_task)
```

## Project Structure

```
Browser/
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Example environment file
├── .venv/                      # Python virtual environment
├── browser_automation_agent.py # Main agent script
├── config.py                   # Configuration loader
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## References

- [Browser Automation Tool Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools-classic/browser-automation-samples)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/)
