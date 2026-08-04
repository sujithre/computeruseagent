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

if not username or not password:
    print("Error: Please set NOVARTIS_USERNAME and NOVARTIS_PASSWORD in .env file")
    exit(1)

# Import and run the computer use agent
from computer_use_agent_new import run_with_playwright

task = f"""
Your goal is to sign into the Novartis Identity Self Service portal and open the "My Access" section.

Steps:
1. You are on the Novartis Identity Self Service sign in page
2. Locate the "Sign In" form
3. In the "User ID" field, enter the username: {username}
4. In the "Password" field, enter the password: {password}
5. Click the "Sign in" button to complete login
6. Wait for the home page with the tiles to load
7. Find the "My Access" tile (the blue tile that says "See what you have access to for others")
8. Click on the "My Access" tile
9. Confirm you have reached the "My Access" page

Report what you see on the final page.
"""

if __name__ == "__main__":
    print("Starting Novartis Identity Self Service automation...")
    print(f"Username: {username}")
    print("Password: ********")
    print("-" * 50)
    
    run_with_playwright(
        task=task,
        start_url="https://www.aps-oem-dev.novartis.com/index/identity/faces/signin",
        width=800,
        height=600,
        headless=False  # Set to True to run without visible browser
    )
