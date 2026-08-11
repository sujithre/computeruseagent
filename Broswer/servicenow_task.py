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


def _first_visible(page, locators):
    """Return the first locator that resolves to a visible element."""
    for build in locators:
        try:
            locator = build()
            locator.wait_for(state="visible", timeout=5000)
            return locator
        except Exception:
            continue
    return None


def login(page):
    """Sign in with Playwright so credentials never go through the model."""
    page.wait_for_load_state("domcontentloaded")

    user_field = _first_visible(page, [
        lambda: page.get_by_label("User ID"),
        lambda: page.locator("#userid"),
        lambda: page.locator("input[name='userid']"),
        lambda: page.locator("input[type='text']").first,
    ])
    if user_field is None:
        raise RuntimeError("Could not find the User ID field on the sign in page.")

    pass_field = _first_visible(page, [
        lambda: page.get_by_label("Password"),
        lambda: page.locator("#password"),
        lambda: page.locator("input[type='password']").first,
    ])
    if pass_field is None:
        raise RuntimeError("Could not find the Password field on the sign in page.")

    user_field.fill(username)
    pass_field.fill(password)
    print("Credentials entered. Signing in...")

    sign_in = _first_visible(page, [
        lambda: page.get_by_role("button", name="Sign In"),
        lambda: page.locator("#btnActiveLogin"),
        lambda: page.locator("input[type='submit']").first,
    ])
    if sign_in is not None:
        sign_in.click()
    else:
        pass_field.press("Enter")

    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    print(f"Signed in. Current page: {page.url}")


task = """
You are on the Novartis Identity Self Service home page, already signed in.

Steps:
1. Look at the tiles on the home page
2. Find the "My Access" tile (the blue tile that says "See what you have access to for others")
3. Click on the "My Access" tile
4. Confirm you have reached the "My Access" page

Report what you see on the final page.
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
        headless=False,  # Set to True to run without visible browser
        setup=login
    )
