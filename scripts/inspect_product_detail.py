"""Inspect product detail page."""
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
        "h1": [page.locator("h1").first.inner_text(timeout=5000)],
        "breadcrumbs": [],
        "logos": [],
        "pdf_links": [],
        "resource_links": [],
        "meta": {},
    }

    for sel in [
        "[class*='breadcrumb' i]",
        "[class*='bread-crumb' i]",
        "nav ol li",
        ".breadcrumb",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            data["breadcrumbs"].append({
                "selector": sel,
                "text": loc.first.inner_text(timeout=3000).strip()[:200],
                "count": loc.count(),
            })

    logos = page.locator("img")
    for i in range(min(logos.count(), 20)):
        img = logos.nth(i)
        if img.is_visible(timeout=1000):
            alt = img.get_attribute("alt") or ""
            src = img.get_attribute("src") or ""
            if "logo" in alt.lower() or "logo" in src.lower() or "partner" in src.lower():
                data["logos"].append({"alt": alt[:60], "src": src[:100]})

    for sel in ["a[href$='.pdf']", "a:has-text('Download')", "a:has-text('PDF')", "a:has-text('Catalog')"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 5)):
            data["pdf_links"].append({
                "text": loc.nth(i).inner_text(timeout=2000).strip()[:60],
                "href": loc.nth(i).get_attribute("href"),
            })

    for sel in ["[class*='resource' i] a", "a:has-text('Documentation')", "a:has-text('Datasheet')"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 5)):
            data["resource_links"].append({
                "text": loc.nth(i).inner_text(timeout=2000).strip()[:60],
                "href": loc.nth(i).get_attribute("href"),
            })

    for key, sel in {
        "description": "meta[name='description']",
        "og_title": "meta[property='og:title']",
        "canonical": "link[rel='canonical']",
    }.items():
        el = page.locator(sel).first
        if el.count():
            data["meta"][key] = el.get_attribute("content") or el.get_attribute("href")

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        inspect(page)
        browser.close()
