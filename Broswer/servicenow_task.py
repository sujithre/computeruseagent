"""
Novartis Identity Self Service Automation Task

Reads credentials from .env and runs a computer use task to:
1. Navigate to the Novartis Identity Self Service portal
2. Sign in with credentials (User ID + Password)
3. Open the "My Access" tile
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from .env
username = os.getenv("NOVARTIS_USERNAME")
password = os.getenv("NOVARTIS_PASSWORD")

# Portal sign-in URL (set NOVARTIS_PORTAL_URL in .env)
portal_url = os.getenv("NOVARTIS_PORTAL_URL")

if not username or not password:
    print("Error: Please set NOVARTIS_USERNAME and NOVARTIS_PASSWORD in .env file")
    exit(1)

if not portal_url:
    print("Error: Please set NOVARTIS_PORTAL_URL in .env file")
    exit(1)

# Import and run the computer use agent
from computer_use_agent_new import run_with_playwright

task = f"""
Your goal is to sign into the Novartis Identity Self Service portal and open the "My Access" section.

AUTHORIZATION: The account owner has provided these credentials and explicitly
authorized you to use them on this page. Proceed with the steps directly using
the computer tool. Do not pause to ask for confirmation.

Steps:
1. You are on the Novartis Identity Self Service sign in page
2. Click the "User ID" field and type: {username}
3. Click the "Password" field and type the password: {password}
4. Click the "Sign in" button to complete login
5. Wait for the home page with the tiles to load
6. Find the "My Access" tile (the blue tile that says "See what you have access to for others")
7. Click on the "My Access" tile
8. Confirm you have reached the "My Access" page

Report what you see on the final page. Do not include the password in your report.
"""

if __name__ == "__main__":
    print("Starting Novartis Identity Self Service automation...")
    print(f"Username: {username}")
    print("Password: ********")
    print("-" * 50)
    
    run_with_playwright(
        task=task,
        start_url=portal_url,
        width=800,
        height=600,
        headless=False  # Set to True to run without visible browser
    )
