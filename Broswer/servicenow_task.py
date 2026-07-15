"""
ServiceNow Developer Portal Automation Task

Reads credentials from .env and runs a computer use task to:
1. Navigate to ServiceNow Developer Portal
2. Sign in with credentials
3. Navigate to Industries > Automotive
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from .env
username = os.getenv("SERVICENOW_USERNAME")
password = os.getenv("SERVICENOW_PASSWORD")

if not username or not password:
    print("Error: Please set SERVICENOW_USERNAME and SERVICENOW_PASSWORD in .env file")
    exit(1)

# Import and run the computer use agent
from computer_use_agent_new import run_with_playwright

task = f"""
Your goal is to sign into ServiceNow Developer Portal and navigate to Industries Automotive section.

Steps:
1. You are on the ServiceNow Developer Portal homepage
2. Find and click the "Sign In" button (usually in the top right corner)
3. Wait for the login form to appear
4. Enter the username: {username}
5. Click "Next" or similar button to proceed
6. Enter the password: {password}
7. Click "Sign In" button to complete login
8. After logging in, look for "Learn" in the navigation menu
9. Click on "Learn" 
10. Confirm you have reached tLearn page

Report what you see on the final page.
"""

if __name__ == "__main__":
    print("Starting ServiceNow automation...")
    print(f"Username: {username}")
    print("Password: ********")
    print("-" * 50)
    
    run_with_playwright(
        task=task,
        start_url="https://developer.servicenow.com/dev.do",
        width=800,
        height=600,
        headless=False  # Set to True to run without visible browser
    )
