"""Extract Partner Spotlight ticket fields from WebSupport for Excel test data."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "testdata" / "_ticket_extract.json"

BASE = "https://websupport.onsumaye.com"
LOGIN_URL = f"{BASE}/login"
USERNAME = __import__("os").environ.get("WEBSUPPORT_USER", "")
PASSWORD = __import__("os").environ.get("WEBSUPPORT_PASS", "")

TICKET_IDS = [
    25102,
    25122,
    25123,
    25103,
    25101,
    25104,
    25116,
    25106,
    25107,
    25108,
    25109,
    25110,
    25111,
    25112,
    25113,
    25114,
]


def _clean(text: str) -> str:
    if not text:
        return ""
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"):
        text = text.replace(ch, " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _label_value_pairs(text: str) -> dict[str, str]:
    """Parse Label: value blocks from ticket description."""
    lines = text.split("\n")
    pairs: dict[str, str] = {}
    current_key = None
    current_vals: list[str] = []

    def flush():
        nonlocal current_key, current_vals
        if current_key is not None:
            pairs[current_key] = "\n".join(current_vals).strip()
        current_key, current_vals = None, []

    for line in lines:
        # Match "Label: value" or "Label :" on its own line
        m = re.match(r"^([A-Za-z][A-Za-z0-9 /&\-()]+?)\s*:\s*(.*)$", line)
        if m and len(m.group(1)) < 80:
            flush()
            current_key = m.group(1).strip()
            rest = m.group(2).strip()
            current_vals = [rest] if rest else []
        elif current_key is not None:
            current_vals.append(line)
        else:
            # preamble / subject lines — keep under _preamble
            pairs.setdefault("_preamble", "")
            pairs["_preamble"] = (pairs["_preamble"] + "\n" + line).strip()
    flush()
    return pairs


def _find_key(pairs: dict[str, str], *candidates: str) -> str:
    lowered = {k.lower().strip(): v for k, v in pairs.items()}
    for cand in candidates:
        c = cand.lower()
        if c in lowered:
            return lowered[c]
        for k, v in lowered.items():
            if c in k or k in c:
                return v
    return ""


def _extract_emails(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")


def _extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s<>\")\]]+", text or "")
    cleaned = []
    for u in urls:
        u = u.rstrip(".,);]")
        if "websupport.onsumaye.com" in u:
            continue
        cleaned.append(u)
    # dedupe preserve order
    seen = set()
    out = []
    for u in cleaned:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def detect_product_type(subject: str, body: str) -> str:
    blob = f"{subject}\n{body}".lower()
    if "application partner showcase" in blob or re.search(r"\bapplication\b", subject.lower()):
        if "system partner showcase" not in subject.lower():
            # Prefer explicit title keywords
            if "application partner showcase" in blob or "application" in subject.lower():
                return "application"
    if "system partner showcase" in blob or re.search(r"\bsystem\b", subject.lower()):
        return "system"
    if "application" in blob and "system" not in subject.lower():
        return "application"
    if "system" in blob:
        return "system"
    return "application"


def map_ticket(ticket_id: int, subject: str, body: str, custom: dict) -> dict:
    body = _clean(body)
    pairs = _label_value_pairs(body)
    # merge custom fields (redmine often has them)
    for k, v in (custom or {}).items():
        if v and str(v).strip():
            pairs[k] = str(v).strip()

    product_name = (
        _find_key(
            pairs,
            "Application Name",
            "Product Name",
            "System Name",
            "Solution Name",
            "Title",
        )
        or subject
    )
    # Clean subject-like "Application Partner Showcase : Name"
    for prefix in (
        "Application Partner Showcase",
        "System Partner Showcase",
        "Partner Spotlight",
        "Edge AI",
    ):
        if product_name.lower().startswith(prefix.lower()):
            product_name = re.sub(rf"^{re.escape(prefix)}\s*[:\-–]\s*", "", product_name, flags=re.I).strip()

    partner_name = _find_key(
        pairs,
        "Partner Display Name",
        "Partner Name",
        "Company Name",
        "Partner",
        "Company",
    )
    partner_dropdown = _find_key(
        pairs,
        "Partner Dropdown",
        "Filter By Partners",
        "Partner Dropdown Label",
        "Partner Display Name",
        "Partner Name",
    ) or partner_name

    short_desc = _find_key(
        pairs,
        "Short Description",
        "Application Short Description",
        "System Short Description",
        "Summary",
    )
    full_desc = _find_key(
        pairs,
        "Description",
        "Application Description",
        "System Description",
        "Full Description",
        "Product Description",
    )
    # Avoid short_desc being same as Description label leak
    if full_desc and short_desc and full_desc == short_desc and len(full_desc) < 40:
        pass

    features = _find_key(
        pairs,
        "Application Features",
        "System Features",
        "Features",
        "Key Features",
    )
    categories = _find_key(
        pairs,
        "Application Categories & Sub-Categories",
        "Application Categories and Sub-Categories",
        "System Categories & Sub-Categories",
        "Categories & Sub-Categories",
        "Categories and Sub-Categories",
        "Application Categories",
        "Categories",
    )

    meta_desc = _find_key(
        pairs,
        "Meta Description",
        "Meta description",
        "expected_meta_description",
        "SEO Description",
    )
    keywords = _find_key(
        pairs,
        "Meta Keywords",
        "Keywords",
        "Meta Keyword",
        "SEO Keywords",
    )
    title = _find_key(
        pairs,
        "Page Title",
        "Meta Title",
        "Detail Title",
        "Title",
        "Application Name",
        "Product Name",
    ) or product_name

    contact_section = _find_key(
        pairs,
        "Partner Contact",
        "Contact",
        "Contact Email",
        "Contact Link",
        "Partner Contact Email",
        "Contact Us",
    )
    resources = _find_key(
        pairs,
        "Application Resources",
        "System Resources",
        "Resources",
        "Resource URL",
        "Resource Links",
        "Links",
    )
    website = _find_key(
        pairs,
        "Partner Website",
        "Website",
        "Company Website",
        "Partner URL",
        "URL",
    )

    emails = _extract_emails(contact_section) or _extract_emails(body)
    urls_contact = _extract_urls(contact_section) + _extract_urls(website)
    resource_urls = _extract_urls(resources)
    if not resource_urls and website:
        resource_urls = _extract_urls(website)

    contact_parts = []
    for e in emails[:2]:
        contact_parts.append(f"mailto:{e}")
    for u in urls_contact[:2]:
        if u not in contact_parts:
            contact_parts.append(u)
    contact_url = "; ".join(contact_parts)
    resource_url = "; ".join(resource_urls[:3])

    product_type = detect_product_type(subject, body)

    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "raw_pairs": {k: v[:500] for k, v in pairs.items() if not k.startswith("_")},
        "partner_name": partner_name,
        "partner_dropdown_label": partner_dropdown,
        "product_name": product_name,
        "product_type": product_type,
        "search_term": product_name,
        "expected_title": title,
        "expected_short_description": short_desc,
        "expected_description": full_desc,
        "expected_meta_description": meta_desc,
        "expected_keywords": keywords,
        "expected_features": features,
        "expected_categories": categories,
        "category_subcategory": categories,
        "expected_contact_url": contact_url,
        "expected_resource_url": resource_url,
        "body_preview": body[:1500],
    }


def login(page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1000)
    # Redmine login fields
    if page.locator("#username").count():
        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.locator('input[name="login"], #login-submit, input[type="submit"]').first.click()
    elif page.locator('input[name="username"]').count():
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.locator('input[type="submit"], button[type="submit"]').first.click()
    else:
        # generic
        page.get_by_label(re.compile("user|login", re.I)).first.fill(USERNAME)
        page.get_by_label(re.compile("pass", re.I)).first.fill(PASSWORD)
        page.locator('input[type="submit"], button[type="submit"]').first.click()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)
    if "login" in page.url.lower():
        raise RuntimeError(f"Login failed, still on {page.url}")


def scrape_ticket(page, ticket_id: int) -> dict:
    url = f"{BASE}/issues/{ticket_id}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    subject = ""
    for sel in ["h2", "#content h2", ".subject h3", ".issue .subject"]:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible(timeout=1000):
                subject = loc.inner_text(timeout=3000).strip()
                if subject:
                    break
        except Exception:
            continue

    # Description wiki / textile
    body = ""
    for sel in [
        ".description .wiki",
        "#issue_description_wiki",
        ".issue .description",
        ".description",
        "#history",
    ]:
        loc = page.locator(sel).first
        try:
            if loc.count():
                text = loc.inner_text(timeout=5000).strip()
                if len(text) > len(body):
                    body = text
        except Exception:
            continue

    # Custom fields table
    custom = {}
    try:
        rows = page.locator(".cf_table tr, .attributes tr, .other-attributes tr, .splitcontentleft table tr")
        for i in range(min(rows.count(), 80)):
            row = rows.nth(i)
            cells = row.locator("th, td")
            if cells.count() >= 2:
                key = cells.nth(0).inner_text(timeout=1000).strip().rstrip(":")
                val = cells.nth(1).inner_text(timeout=1000).strip()
                if key and val and len(key) < 80:
                    custom[key] = val
    except Exception:
        pass

    # Also harvest all attribute labels
    try:
        attrs = page.evaluate(
            """() => {
              const out = {};
              document.querySelectorAll('.attribute, .cf_table tr, .attributes p, label').forEach(el => {
                const t = (el.textContent || '').trim();
                if (t.includes(':') && t.length < 300) {
                  const idx = t.indexOf(':');
                  const k = t.slice(0, idx).trim();
                  const v = t.slice(idx+1).trim();
                  if (k && v) out[k] = v;
                }
              });
              return out;
            }"""
        )
        for k, v in (attrs or {}).items():
            custom.setdefault(k, v)
    except Exception:
        pass

    # Full page main content fallback
    if len(body) < 100:
        try:
            body = page.locator("#content, #main, main").first.inner_text(timeout=5000)
        except Exception:
            body = page.inner_text("body")

    mapped = map_ticket(ticket_id, subject, body, custom)
    mapped["url"] = url
    mapped["custom_fields"] = custom
    return mapped


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        print("Logging in...")
        login(page)
        print("Logged in:", page.url)

        for tid in TICKET_IDS:
            print(f"Scraping {tid}...")
            try:
                data = scrape_ticket(page, tid)
                results.append(data)
                print(
                    f"  OK subject={data.get('subject','')[:60]!r} "
                    f"partner={data.get('partner_name')!r} "
                    f"product={data.get('product_name')!r}"
                )
            except Exception as exc:
                print(f"  FAILED {tid}: {exc}")
                results.append({"ticket_id": tid, "error": str(exc)})

        browser.close()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
