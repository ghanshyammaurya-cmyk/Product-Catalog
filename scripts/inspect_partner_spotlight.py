"""Inspect partner spotlight listing page."""
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

    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')"]:
        try:
            if page.locator(sel).first.is_visible(timeout=2000):
                page.locator(sel).first.click()
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

    data = {
        "url": page.url,
        "title": page.title(),
        "h1": page.locator("h1").all_inner_texts()[:3],
        "breadcrumbs": [],
        "view_toggles": [],
        "product_cards": [],
        "filters": [],
        "search": None,
        "sample_products": [],
    }

    for sel in [
        "[class*='breadcrumb' i] li",
        "nav[aria-label*='readcrumb' i] *",
        ".page-breadcrumb li",
        "[class*='bread' i]",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            texts = []
            for i in range(min(loc.count(), 15)):
                t = loc.nth(i).inner_text(timeout=1000).strip()
                if t:
                    texts.append(t)
            if texts:
                data["breadcrumbs"].append({"selector": sel, "texts": texts[:10]})

    for text in ["Grid", "List", "grid", "list"]:
        loc = page.get_by_role("button", name=text)
        if loc.count() == 0:
            loc = page.locator(f"[class*='{text.lower()}' i]")
        data["view_toggles"].append({"text": text, "count": loc.count()})

    for sel in [
        "[class*='product' i]",
        "[class*='card' i]",
        "[class*='solution' i]",
        "[class*='partner' i] a",
        "article",
        ".catalog-item",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            samples = []
            for i in range(min(loc.count(), 3)):
                samples.append(loc.nth(i).inner_text(timeout=2000).strip()[:120])
            data["product_cards"].append({"selector": sel, "count": loc.count(), "samples": samples})

    search = page.locator("input[placeholder*='Search' i]").first
    if search.is_visible(timeout=3000):
        data["search"] = {
            "placeholder": search.get_attribute("placeholder"),
            "selector": "input[placeholder*='Search' i]",
        }

    # Get first few product links
    links = page.locator("a[href*='partner-spotlight']").filter(has=page.locator("img"))
    for i in range(min(links.count(), 5)):
        data["sample_products"].append({
            "text": links.nth(i).inner_text(timeout=2000).strip()[:80],
            "href": links.nth(i).get_attribute("href"),
        })

    # product detail links
    detail_links = page.locator("a[href*='/partner-spotlight/']")
    for i in range(min(detail_links.count(), 8)):
        data.setdefault("detail_links", []).append({
            "text": detail_links.nth(i).inner_text(timeout=2000).strip()[:80],
            "href": detail_links.nth(i).get_attribute("href"),
        })

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        inspect(page)
        browser.close()
