import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    page = p.chromium.launch(headless=True).new_page(viewport={"width":1920,"height":1080})
    page.goto("https://builders.intel.com", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    try: page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
    except: pass

    nav = []
    for a in page.locator("nav a, header a, [class*='nav' i] a").all()[:80]:
        try:
            t = a.inner_text(timeout=500).strip()
            h = a.get_attribute("href") or ""
            if t and len(t) < 40:
                nav.append({"text": t, "href": h[:80]})
        except: pass
    print("NAV LINKS:", json.dumps([x for x in nav if any(k in x["text"].lower() for k in ["engagement","solution","edge","catalog"])][:20], indent=2))

    page.goto("https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=system")
    page.wait_for_timeout(5000)
    sel = page.locator("select[name*='partner' i], select").first
    if sel.count():
        name = sel.get_attribute("name")
        opts = sel.locator("option").all_inner_texts()[:15]
        print("PARTNER SELECT:", name, opts)

    # application type tabs
    for t in ["Edge AI System", "Edge AI Application"]:
        print(t, page.get_by_text(t, exact=False).count())

    # first listview full structure
    lv = page.locator(".listview").first
    print("LISTVIEW HTML classes parent:", lv.evaluate("el => el.className"))
    print("LISTVIEW TEXT:\n", lv.inner_text(timeout=5000)[:700])

    # detail features/resources
    page.locator("a:has-text('Advantech UNO-258')").first.click()
    page.wait_for_timeout(5000)
    body = page.locator("main, [class*='product-detail' i], .container").first
    text = body.inner_text(timeout=8000) if body.count() else page.inner_text("body")[:3000]
    for kw in ["Features", "Resources", "Description", "Categories"]:
        print(kw, "in page:", kw.lower() in text.lower())

    # all h2 on detail with following sibling text
    for i in range(page.locator("h2").count()):
        h = page.locator("h2").nth(i).inner_text(timeout=1000).strip()
        if h and "Subscribe" not in h and "Oops" not in h and "Manage" not in h:
            print("H2:", h)

    page.context.browser.close()
