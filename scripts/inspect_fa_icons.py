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
    except Exception:
        pass

    icons = page.locator("i[class*='fa-']")
    data = []
    for i in range(min(icons.count(), 50)):
        cls = icons.nth(i).get_attribute("class") or ""
        if "fa-th" in cls or "grid" in cls.lower() or "list" in cls.lower():
            parent = icons.nth(i).locator("xpath=..")
            data.append({"class": cls, "parent_tag": parent.evaluate("el => el.tagName"), "parent_class": parent.get_attribute("class")})

    # view wrapper
    view_wrap = page.locator("[class*='view' i]")
    for i in range(min(view_wrap.count(), 20)):
        cls = view_wrap.nth(i).get_attribute("class") or ""
        if "grid" in cls.lower() or "list" in cls.lower():
            data.append({"view_wrap_class": cls, "text": view_wrap.nth(i).inner_text(timeout=500)[:40]})

    print(json.dumps(data, indent=2))
    browser.close()
