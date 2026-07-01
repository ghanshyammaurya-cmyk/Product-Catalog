"""Inspect product detail content selectors."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

DETAIL_URL = (
    "https://builders.intel.com/ecosystem-engagement/solution-hub/"
    "edge-ai-catalog/partner-spotlight/advantech-uno-258-189"
)


def inspect(page):
    page.goto(DETAIL_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    for sel in ["#onetrust-accept-btn-handler"]:
        try:
            if page.locator(sel).first.is_visible(timeout=2000):
                page.locator(sel).first.click()
        except Exception:
            pass

    data = {"headings": [], "download_links": [], "resource_section": []}

    for tag in ["h1", "h2", "h3", "h4"]:
        loc = page.locator(tag)
        for i in range(min(loc.count(), 8)):
            t = loc.nth(i).inner_text(timeout=2000).strip()
            if t:
                data["headings"].append({"tag": tag, "text": t[:100]})

    for sel in [
        "a:has-text('Download')",
        "a:has-text('Offline')",
        "a:has-text('Datasheet')",
        "a:has-text('Resource')",
        "a[href*='download' i]",
        "[class*='resource' i] a",
        "[class*='download' i] a",
    ]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 5)):
            data["download_links"].append({
                "selector": sel,
                "text": loc.nth(i).inner_text(timeout=2000).strip()[:80],
                "href": (loc.nth(i).get_attribute("href") or "")[:120],
            })

    body_text = page.locator("[class*='product' i], [class*='detail' i], main").first
    if body_text.count():
        data["main_text_sample"] = body_text.inner_text(timeout=5000)[:500]

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        inspect(page)
        browser.close()
