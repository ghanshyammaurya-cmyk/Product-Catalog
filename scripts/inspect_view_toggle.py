import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

URL = "https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=system"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":1920,"height":1080})
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    try:
        page.locator("#onetrust-accept-btn-handler").first.click(timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    results = []
    for sel in [
        "button", "a", "span", "i", "div[role='button']",
    ]:
        loc = page.locator(sel)
        for i in range(min(loc.count(), 200)):
            el = loc.nth(i)
            try:
                if not el.is_visible(timeout=100):
                    continue
                text = el.inner_text(timeout=500).strip()
                cls = el.get_attribute("class") or ""
                aria = el.get_attribute("aria-label") or ""
                title = el.get_attribute("title") or ""
                combined = f"{text} {cls} {aria} {title}".lower()
                if ("grid" in combined or "list" in combined) and len(text) < 20:
                    if "cookie" not in combined:
                        results.append({
                            "sel": sel, "text": text[:30], "class": cls[:60],
                            "aria": aria[:40], "title": title[:40]
                        })
            except Exception:
                pass

    # dedupe
    seen = set()
    unique = []
    for r in results:
        key = (r["text"], r["class"], r["aria"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(json.dumps(unique[:20], indent=2))
    browser.close()
