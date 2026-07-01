"""One-off helper to list Partner Spotlight products."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

URL = (
    "https://builders.intel.com/ecosystem-engagement/solution-hub/"
    "edge-ai-catalog/partner-spotlight?type=system"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    try:
        page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    links = page.locator("a[href*='/partner-spotlight/'][href*='-']").all()
    seen = set()
    for link in links[:40]:
        text = link.inner_text().strip().split("\n")[0]
        href = link.get_attribute("href")
        if text and len(text) > 3 and text not in seen:
            seen.add(text)
            print(f"{text} | {href}")
    browser.close()
