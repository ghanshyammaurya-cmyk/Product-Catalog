import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import pandas as pd
from playwright.sync_api import sync_playwright

from utilities.category_parser import parse_category_subcategory_pairs
from utilities.category_validator import CategoryValidator, normalize_category_text

val = pd.read_excel(
    os.path.join(ROOT, "testdata", "partner_products.xlsx"), sheet_name="PartnerProducts"
)
pairs = parse_category_subcategory_pairs(
    val[val.test_id == "PS-004"].iloc[0].category_subcategory
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(
        "https://builders.intel.com/ecosystem-engagement/solution-hub/edge-ai-catalog/partner-spotlight?type=application&pSearch=Smart+IoT+Vending+Fridge",
        wait_until="load",
        timeout=90000,
    )
    page.wait_for_timeout(2000)
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept All')"]:
        btn = page.locator(sel).first
        if btn.count():
            try:
                btn.click(timeout=2000)
                break
            except Exception:
                pass
    page.get_by_role("link", name="Smart IoT Vending Fridge", exact=True).first.click()
    page.wait_for_load_state("load")
    page.wait_for_timeout(5000)
    body = page.inner_text("body")
    out = os.path.join(ROOT, "downloads", "detail_body.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print("body len", len(body))
    for term in [
        "Self-Checkout",
        "Worldwide",
        "Device Type",
        "Retail",
        "OpenVINO",
        "Categories",
    ]:
        print(term, term.lower() in normalize_category_text(body))
    v = CategoryValidator(page)
    data = v.collect_detail_site_data()
    print("haystack len", len(data["haystack"]))
    ok, msg, found, missing = v.validate_pairs_strict(pairs, data)
    print("ok", ok, "found", len(found), "missing", len(missing))
    for m in missing:
        print("MISSING", m["category"], "|", m["subcategory"])
    browser.close()
