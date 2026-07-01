"""Inspect search behavior on partner spotlight."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

SPOTLIGHT_URL = (
    "https://builders.intel.com/ecosystem-engagement/solution-hub/"
    "edge-ai-catalog/partner-spotlight?type=system"
)


def inspect(page):
    page.goto(SPOTLIGHT_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    for sel in ["#onetrust-accept-btn-handler"]:
        try:
            if page.locator(sel).first.is_visible(timeout=2000):
                page.locator(sel).first.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

    search = page.locator("input[placeholder*='Search by Keywords' i]").first
    search.fill("Advantech")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    data = {
        "url_after_search": page.url,
        "product_links": [],
        "grid_list": {},
    }

    links = page.locator("a[href*='/partner-spotlight/'][href*='-']")
    for i in range(min(links.count(), 5)):
        t = links.nth(i).inner_text(timeout=2000).strip()
        if t:
            data["product_links"].append(t)

    for name in ["Grid", "List"]:
        btn = page.get_by_role("button", name=name)
        data["grid_list"][name] = btn.count()

    # grid view button more specific
    grid_btn = page.locator("[class*='grid' i][class*='view' i], button[class*='grid' i]").first
    data["grid_list"]["grid_class_btn"] = grid_btn.count()

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        inspect(page)
        browser.close()
