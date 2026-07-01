"""One-off site inspector — run to dump selectors from live catalog page."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

CATALOG_URL = "https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog"


def inspect(page):
    page.goto(CATALOG_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # Cookie
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')"]:
        if page.locator(sel).first.is_visible(timeout=2000):
            page.locator(sel).first.click()
            page.wait_for_timeout(1000)
            break

    data = {
        "url": page.url,
        "title": page.title(),
        "h1": page.locator("h1").all_inner_texts()[:5],
        "breadcrumb_candidates": [],
        "search_inputs": [],
        "grid_list_buttons": [],
        "partner_links": [],
        "nav_links": [],
        "see_all_links": [],
    }

    for sel in [
        "nav[aria-label*='readcrumb' i] li",
        "[class*='breadcrumb' i] li",
        "ol li",
        ".breadcrumb li",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            texts = [loc.nth(i).inner_text(timeout=2000).strip() for i in range(min(loc.count(), 10))]
            data["breadcrumb_candidates"].append({"selector": sel, "texts": texts})

    for sel in ["input[type='search']", "input[placeholder*='Search' i]", "input[placeholder*='search' i]", "[class*='search' i] input"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 3)):
            el = loc.nth(i)
            if el.is_visible(timeout=1000):
                data["search_inputs"].append({
                    "selector": sel,
                    "placeholder": el.get_attribute("placeholder"),
                    "visible": True,
                })

    for sel in ["button", "[role='button']", "a"]:
        pass

    for text in ["Grid", "List", "Partner Spotlight", "See All"]:
        loc = page.get_by_text(text, exact=False)
        data["nav_links"].append({"text": text, "count": loc.count()})

    for sel in ["a[href*='partner']", "a:has-text('Partner Spotlight')", "a:has-text('See All')"]:
        loc = page.locator(sel)
        hrefs = []
        for i in range(min(loc.count(), 8)):
            hrefs.append({"text": loc.nth(i).inner_text(timeout=2000).strip()[:80], "href": loc.nth(i).get_attribute("href")})
        data["partner_links"].append({"selector": sel, "items": hrefs})

    # systems catalog link
    systems = page.locator("a:has-text('See All Intel')")
    for i in range(min(systems.count(), 5)):
        data["see_all_links"].append({
            "text": systems.nth(i).inner_text(timeout=2000).strip(),
            "href": systems.nth(i).get_attribute("href"),
        })

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        inspect(page)
        browser.close()
