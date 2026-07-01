"""Debug PS-004 listing card."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

URL = "https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=application"
PRODUCT = "Smart IoT Vending Fridge"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    try:
        page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
    except Exception:
        pass
    page.fill("input#pSearch", PRODUCT)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    lines = []
    lines.append(f"url={page.url}")
    lines.append(f"product_links={page.locator('a:has-text(\"Smart IoT Vending Fridge\")').count()}")

    for sel in [
        f".listview:has-text('{PRODUCT}')",
        f".gridview:has-text('{PRODUCT}')",
        f".listview, .gridview:has(a:has-text('{PRODUCT}'))",
    ]:
        c = page.locator(sel).first
        lines.append(f"selector {sel} count={c.count()}")
        if c.count():
            lines.append(c.inner_text()[:500])

    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "ps004_card.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n---\n".join(lines))
    print("done")
    b.close()
