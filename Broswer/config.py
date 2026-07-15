"""
Configuration module for Azure AI Foundry Browser Automation Agent.
Loads environment variables from .env file.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_required_env(var_name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {var_name}. "
            f"Please set it in your .env file."
        )
    return value


# Azure AI Foundry Project Endpoint
PROJECT_ENDPOINT = get_required_env("PROJECT_ENDPOINT")

# Playwright Connection Name (for Browser Automation)
AZURE_PLAYWRIGHT_CONNECTION_NAME = get_required_env("AZURE_PLAYWRIGHT_CONNECTION_NAME")

# Model Deployment Name (for Browser Automation)
MODEL_DEPLOYMENT_NAME = get_required_env("MODEL_DEPLOYMENT_NAME")

# Computer Use Model Deployment Name
# This is typically a different model deployment that supports computer use
COMPUTER_USE_MODEL_DEPLOYMENT_NAME = os.getenv("COMPUTER_USE_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME)

# Computer Use Environment (windows, mac, linux, browser)
COMPUTER_USE_ENVIRONMENT = os.getenv("COMPUTER_USE_ENVIRONMENT", "windows")
