"""Inspect DOM for full 26-step flow."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

BASE = "https://builders.intel.com"


def accept(page):
    try:
        page.locator("#onetrust-accept-btn-handler").first.click(timeout=3000)
        page.wait_for_timeout(800)
    except Exception:
        pass


def dump(page, label, data):
    print(f"\n=== {label} ===")
    print(json.dumps(data, indent=2))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    # Step 1-3: menu navigation
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    accept(page)

    menu = {}
    for text in ["Engagement", "Solution Hub", "Edge AI Catalog"]:
        loc = page.get_by_role("link", name=text)
        menu[text] = {"count": loc.count(), "visible": loc.first.is_visible() if loc.count() else False}
    dump(page, "MENU", menu)

    # Try hover Engagement
    try:
        page.get_by_role("link", name="Engagement").first.hover()
        page.wait_for_timeout(1500)
        sh = page.get_by_role("link", name="Edge AI Catalog")
        menu["edge_after_hover"] = sh.count()
    except Exception as e:
        menu["hover_error"] = str(e)

    # Step 4: catalog page explore link
    page.goto(f"{BASE}/ecosystem-engagement/solution-hub/edge-ai-catalog", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    accept(page)
    explore = page.locator("a:has-text('Explore Partner Spotlight')")
    dump(page, "EXPLORE", [{"text": explore.nth(i).inner_text(timeout=2000), "href": explore.nth(i).get_attribute("href")} for i in range(min(explore.count(), 3))])

    # Step 5-14: spotlight listing
    page.goto(f"{BASE}/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=system", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    accept(page)

    listing = {}
    # partner dropdown
    for sel in ["select", "[class*='partner' i] select", "select[name*='partner' i]", "[class*='dropdown' i]", "button:has-text('Partner')"]:
        loc = page.locator(sel)
        if loc.count():
            listing.setdefault("partner_filters", []).append({"sel": sel, "count": loc.count()})

    # listing card fields for Advantech
    ps = page.locator("#pSearch")
    if ps.count():
        ps.fill("Advantech")
        ps.press("Enter")
        page.wait_for_timeout(3000)

    card = page.locator(".listview").first
    if card.count():
        listing["card_text_sample"] = card.inner_text(timeout=5000)[:500]

    listing["quick_view"] = page.locator("a.quick-view, a:has-text('Quick View')").count()
    listing["product_details_links"] = page.locator("a:has-text('Product Details')").count()
    listing["eye_icons"] = page.locator("[class*='eye' i], i.fa-eye, a[title*='View' i]").count()
    listing["logos_on_listing"] = page.locator("img[src*='companyLogo' i]").count()

  # filters sidebar
    sidebar = page.locator("[class*='sidebar' i], aside").first
    if sidebar.count():
        listing["sidebar_text"] = sidebar.inner_text(timeout=5000)[:800]

    dump(page, "LISTING", listing)

    # Step 15-26: detail page
    page.locator("a:has-text('Advantech UNO-258')").first.click()
    page.wait_for_timeout(5000)
    accept(page)

    detail = {"url": page.url, "title": page.title()}
    for tag in ["h1", "h2", "h3", "h4"]:
        loc = page.locator(tag)
        detail[tag] = [loc.nth(i).inner_text(timeout=2000).strip()[:80] for i in range(min(loc.count(), 8)) if loc.nth(i).inner_text(timeout=2000).strip()]

    detail["thumbnail"] = []
    for img in page.locator("img").all()[:15]:
        if img.is_visible():
            detail["thumbnail"].append({"alt": (img.get_attribute("alt") or "")[:60], "src": (img.get_attribute("src") or "")[:80]})

    detail["contact_links"] = []
    for sel in ["a:has-text('Contact')", "a:has-text('Partner Contact')", "a[href*='contact' i]", "a[href*='mailto:' i]"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 5)):
            detail["contact_links"].append({"sel": sel, "text": loc.nth(i).inner_text(timeout=2000).strip()[:50], "href": (loc.nth(i).get_attribute("href") or "")[:80]})

    detail["features"] = page.locator("[class*='feature' i]").first.inner_text(timeout=3000)[:400] if page.locator("[class*='feature' i]").count() else ""
    detail["resources"] = []
    for sel in ["[class*='resource' i] a", "a:has-text('Resource')", "a.trackpdfdwload"]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 8)):
            detail["resources"].append({"text": loc.nth(i).inner_text(timeout=2000).strip()[:50], "href": (loc.nth(i).get_attribute("href") or "")[:80]})

    detail["categories_section"] = page.locator(":text-is('Categories'), h2:has-text('Categories'), [class*='categor' i]").count()
    detail["related"] = page.locator("h2:has-text('Related Products')").count()
    if detail["related"]:
        rp = page.locator("h2:has-text('Related Products')").locator("xpath=..")
        detail["related_text"] = rp.inner_text(timeout=5000)[:400]

    detail["breadcrumb"] = page.locator(".breadcrumb").first.inner_text(timeout=3000) if page.locator(".breadcrumb").count() else ""
    detail["description_blocks"] = page.locator("[class*='description' i], [class*='product-detail' i]").first.inner_text(timeout=5000)[:600] if page.locator("[class*='description' i]").count() else ""

    dump(page, "DETAIL", detail)
    browser.close()
