"""Inspect filters, grid/list, in-page search on partner spotlight."""
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
    page.wait_for_timeout(6000)

    for sel in ["#onetrust-accept-btn-handler"]:
        try:
            if page.locator(sel).first.is_visible(timeout=2000):
                page.locator(sel).first.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

    data = {"filters": [], "grid_list": [], "search_fields": [], "product_title_on_page": []}

    # All inputs on page
    inputs = page.locator("input:visible")
    for i in range(min(inputs.count(), 10)):
        inp = inputs.nth(i)
        data["search_fields"].append({
            "placeholder": inp.get_attribute("placeholder"),
            "name": inp.get_attribute("name"),
            "id": inp.get_attribute("id"),
            "type": inp.get_attribute("type"),
        })

    # Grid list - look for icons/buttons near product listing
    for sel in [
        "button[title*='Grid' i]",
        "button[title*='List' i]",
        "[aria-label*='Grid' i]",
        "[aria-label*='List' i]",
        ".grid-view",
        ".list-view",
        "[class*='view-type' i]",
        "[class*='grid-icon' i]",
        "[class*='list-icon' i]",
        "i[class*='grid' i]",
        "span[class*='grid' i]",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            data["grid_list"].append({"selector": sel, "count": loc.count()})

    # Category/filter sidebar
    for sel in [
        "[class*='filter' i] a",
        "[class*='category' i] a",
        "[class*='facet' i] a",
        "aside a",
        "[class*='sidebar' i] a",
    ]:
        loc = page.locator(sel)
        if loc.count() > 3:
            samples = []
            for i in range(min(loc.count(), 8)):
                t = loc.nth(i).inner_text(timeout=1000).strip()
                if t and len(t) < 50:
                    samples.append(t)
            if samples:
                data["filters"].append({"selector": sel, "samples": samples[:8]})

    # Product names on listing
    for sel in ["h2", "h3", "[class*='product-title' i]", "[class*='card-title' i]"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 5)):
            t = loc.nth(i).inner_text(timeout=2000).strip()
            if t:
                data["product_title_on_page"].append({"selector": sel, "text": t[:80]})

    # Try in-page filter search (not header)
    main_search = page.locator("main input[placeholder*='Search' i], [class*='catalog' i] input, [class*='spotlight' i] input").first
    if main_search.count() and main_search.is_visible(timeout=2000):
        before_url = page.url
        main_search.fill("Advantech")
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        data["in_page_search"] = {"before": before_url, "after": page.url}

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        inspect(page)
        browser.close()
