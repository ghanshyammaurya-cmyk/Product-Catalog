import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from playwright.sync_api import sync_playwright

URL = (
    "https://builders.intel.com/ecosystem-engagement/solution-hub/"
    "edge-ai-catalog/partner-spotlight?type=system"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    try:
        page.locator("#onetrust-accept-btn-handler").first.click(timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    def snapshot(label):
        return page.evaluate(
            """() => {
                const out = {buttons: [], gridview: 0, listview: 0, samples: []};
                document.querySelectorAll('button').forEach((b) => {
                    const t = (b.textContent || '').trim();
                    const c = b.className || '';
                    const html = b.innerHTML || '';
                    if (/grid|list|th-large|th-list|fa-th/i.test(t + c + html)) {
                        out.buttons.push({
                            text: t.slice(0, 40),
                            class: String(c).slice(0, 100),
                            active: /active|selected|current/i.test(c),
                            html: html.slice(0, 150),
                        });
                    }
                });
                out.gridview = document.querySelectorAll('.gridview').length;
                out.listview = document.querySelectorAll('.listview').length;
                document.querySelectorAll('.gridview, .listview').forEach((el, i) => {
                    if (i < 3) out.samples.push(el.className.slice(0, 100));
                });
                return out;
            }"""
        )

    before = snapshot("before")
    # click grid if found
    for sel in [
        "button:has(i.fa-th-large)",
        "button:has(i.fa-th)",
        "button.btn:has(i.fa-th-large)",
        "[title*='Grid' i]",
        "[aria-label*='Grid' i]",
    ]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible(timeout=1000):
                loc.click()
                page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    after_grid = snapshot("after_grid")

    for sel in [
        "button:has(i.fa-th-list)",
        "button.btn:has(i.fa-th-list)",
        "[title*='List' i]",
    ]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible(timeout=1000):
                loc.click()
                page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    after_list = snapshot("after_list")

    print(json.dumps({"before": before, "after_grid": after_grid, "after_list": after_list}, indent=2))
    browser.close()
