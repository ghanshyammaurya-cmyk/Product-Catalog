"""Inspect Partner Spotlight DOM for partner dropdown and catalog count."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

URL = (
    "https://builders.intel.com/ecosystem-engagement/solution-hub/"
    "edge-ai-catalog/partner-spotlight?type=system"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    try:
        page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
    except Exception:
        pass
    page.wait_for_timeout(2000)

    out = []
    loc = page.locator("h2").filter(has_text="Unique Products")
    if loc.count():
        out.append("COUNT: " + loc.first.inner_text())

    for sel in [
        "button:has-text('Filter By Partners')",
        ".multiselect",
        "button.dropdown-toggle",
        "#ecosystemPartner + button",
        ".multiselect-native-select button",
    ]:
        el = page.locator(sel)
        out.append(f"{sel} count={el.count()}")

    btn = page.locator("button:has-text('Filter By Partners')").first
    if not btn.count():
        btn = page.locator(".multiselect button.dropdown-toggle").first
    if btn.count():
        btn.click()
        page.wait_for_timeout(1000)
        out.append("opened partner dropdown")
        inp = page.locator(
            ".multiselect-container input[type='text'], "
            ".dropdown-menu input, .multiselect-filter input"
        ).first
        if inp.count():
            inp.fill("ad")
            page.wait_for_timeout(800)
            labels = page.locator(
                ".multiselect-container label, .dropdown-menu label"
            ).all_inner_texts()[:8]
            out.append("labels: " + str(labels))

    page.locator("a:has-text('Product Details')").first.click()
    page.wait_for_timeout(4000)
    contacts = page.locator(
        "a:has-text('Contact'), button:has-text('Contact')"
    ).all_inner_texts()[:5]
    out.append("contacts: " + str(contacts))

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "reports", "inspect_out.txt"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Wrote", out_path)

    browser.close()
