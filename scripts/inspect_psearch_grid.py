import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

URL = "https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=system"

with sync_playwright() as p:
    page = p.chromium.launch(headless=True).new_page(viewport={"width":1920,"height":1080})
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    try:
        page.locator("#onetrust-accept-btn-handler").first.click(timeout=3000)
    except Exception:
        pass

    # pSearch
    ps = page.locator("#pSearch")
    ps.fill("Advantech")
    ps.press("Enter")
    page.wait_for_timeout(4000)

    products = page.locator("a[href*='/partner-spotlight/'][href*='-']")
    product_names = []
    for i in range(min(products.count(), 10)):
        t = products.nth(i).inner_text(timeout=2000).strip()
        if t and t not in ("Product Details", "Read more"):
            product_names.append(t)

    # grid/list aria labels
    toggles = []
    for el in page.locator("[aria-label]").all()[:30]:
        label = el.get_attribute("aria-label") or ""
        if "grid" in label.lower() or "list" in label.lower():
            toggles.append(label)

    print(json.dumps({
        "url": page.url,
        "products_after_psearch": product_names[:5],
        "product_count": products.count(),
        "view_aria_labels": toggles,
    }, indent=2))
    page.context.browser.close()
