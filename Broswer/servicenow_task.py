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


def _first_visible(scope, locators):
    """Return the first locator that resolves to a visible element."""
    for build in locators:
        try:
            locator = build(scope)
            locator.wait_for(state="visible", timeout=5000)
            return locator
        except Exception:
            continue
    return None


def _find_in_frames(page, locators):
    """Search the main frame and every child frame for the first match."""
    for frame in [page] + list(page.frames):
        found = _first_visible(frame, locators)
        if found is not None:
            return found
    return None


def _dump_inputs(page):
    """Print the input fields found on the page to help debug selectors."""
    print("\n--- Input fields detected ---")
    for frame in [page] + list(page.frames):
        try:
            inputs = frame.locator("input")
            for i in range(inputs.count()):
                el = inputs.nth(i)
                print(f"  type={el.get_attribute('type')} id={el.get_attribute('id')} "
                      f"name={el.get_attribute('name')} visible={el.is_visible()}")
        except Exception:
            continue
    print("--- end ---\n")


def _type_into(field, value, label):
    """Click, clear, and type a value, verifying it landed in the field."""
    field.click()
    try:
        field.fill("")
    except Exception:
        pass
    field.type(value, delay=60)
    try:
        actual = field.input_value()
    except Exception:
        actual = None
    if actual is not None and actual != value:
        print(f"  Warning: {label} shows '{actual}' after typing.")
    else:
        print(f"  {label} entered.")


def login(page):
    """Sign in with Playwright so credentials never go through the model."""
    page.wait_for_load_state("domcontentloaded")

    user_field = _find_in_frames(page, [
        lambda s: s.get_by_label("User ID"),
        lambda s: s.locator("#userid"),
        lambda s: s.locator("input[name='userid']"),
        lambda s: s.locator("input[type='text']:visible").first,
    ])
    pass_field = _find_in_frames(page, [
        lambda s: s.get_by_label("Password"),
        lambda s: s.locator("#password"),
        lambda s: s.locator("input[type='password']:visible").first,
    ])

    if user_field is None or pass_field is None:
        _dump_inputs(page)
        raise RuntimeError("Could not find the sign in fields. See the list above.")

    _type_into(user_field, username, "User ID")
    _type_into(pass_field, password, "Password")
    print("Signing in...")

    sign_in = _find_in_frames(page, [
        lambda s: s.get_by_role("button", name="Sign In"),
        lambda s: s.locator("#btnActiveLogin"),
        lambda s: s.locator("input[type='submit']").first,
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
