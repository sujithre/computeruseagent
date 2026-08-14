"""
Computer Use smoke test.

Runs the same agent loop against a public site with no login, so we can tell
whether "no computer calls" is caused by the code/configuration or by the
internal portal specifically.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from computer_use_agent_new import run_with_playwright

task = """
You are on the Bing home page.

Steps:
1. Click the search box
2. Type: Microsoft Azure
3. Press Enter
4. Report the titles of the first few search results you can see
"""

if __name__ == "__main__":
    print("Computer Use smoke test against a public site")
    print("-" * 50)

    run_with_playwright(
        task=task,
        start_url=os.getenv("SMOKE_TEST_URL", "https://www.bing.com"),
        width=800,
        height=600,
        headless=False,
        max_iterations=8,
    )
