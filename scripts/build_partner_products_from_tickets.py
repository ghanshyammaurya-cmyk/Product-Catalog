"""Build partner_products.xlsx from scraped WebSupport ticket JSON / re-fetch."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_XLSX = ROOT / "testdata" / "partner_products.xlsx"
OUT_JSON = ROOT / "testdata" / "_ticket_extract.json"

BASE = "https://websupport.onsumaye.com"
USERNAME = os.environ.get("WEBSUPPORT_USER", "")
PASSWORD = os.environ.get("WEBSUPPORT_PASS", "")

TICKET_IDS = [
    25102, 25122, 25123, 25103, 25101, 25104, 25116, 25106,
    25107, 25108, 25109, 25110, 25111, 25112, 25113, 25114,
]

KNOWN_LABELS = [
    "Partner Name",
    "Partner Display Name",
    "Application Name",
    "Product Name",
    "System Name",
    "Application Short Description",
    "Product Short Description",
    "System Short Description",
    "Short Description",
    "Application Description",
    "Product Description",
    "System Description",
    "Description",
    "Partner Contact",
    "Application Features",
    "Product Features",
    "System Features",
    "Features",
    "Application Resources",
    "Product Resources",
    "System Resources",
    "Resources",
    "Application Image",
    "Product Image",
    "System Image",
    "Application Categories & Sub-Categories",
    "Product Categories & Sub-Categories",
    "System Categories & Sub-Categories",
    "Categories & Sub-Categories",
    "Device Type",
    "Vertical",
    "Use Cases",
    "Open Software Platform",
    "Intel Technologies",
    "Intel Processors",
    "Intel Graphics",
    "Geo Availability",
    "Edge Feature",
    "AI Edge System Sizing",
    "Target Audience",
    "Meta Description",
    "Meta Keywords",
    "Page Title",
    "Partner Website",
    "Website",
]


def _clean(text: str) -> str:
    if not text:
        return ""
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"):
        text = text.replace(ch, " ")
    # normalize common mojibake for ® ™ —
    text = text.replace("�", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _http_get(opener, url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (QA-Automation)"})
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _http_post(opener, url: str, data: dict) -> str:
    body = urlencode(data).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0 (QA-Automation)",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def login(opener) -> None:
    html = _http_get(opener, f"{BASE}/login")
    token = ""
    m = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', html) or re.search(
        r'value="([^"]+)"[^>]*name="authenticity_token"', html
    )
    if m:
        token = m.group(1)
    payload = {"username": USERNAME, "password": PASSWORD, "login": "Login"}
    if token:
        payload["authenticity_token"] = token
    _http_post(opener, f"{BASE}/login", payload)


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>", "\n", html)
    html = re.sub(r"(?is)</div>", "\n", html)
    html = re.sub(r"(?is)</li>", "\n", html)
    html = re.sub(r"(?is)</h[1-6]>", "\n", html)
    html = re.sub(r"(?is)<li[^>]*>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n[ \t]+", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def extract_subject(html: str) -> str:
    m = re.search(r"<h2[^>]*>\s*(?:<[^>]+>\s*)*([^<]+)", html, re.I)
    if m:
        return _clean(m.group(1))
    return ""


def extract_description_html(html: str) -> str:
    m = re.search(
        r'(?is)<div[^>]*class="[^"]*description[^"]*"[^>]*>.*?<div[^>]*class="[^"]*wiki[^"]*"[^>]*>(.*?)</div>',
        html,
    )
    if m:
        return strip_tags(m.group(1))
    m = re.search(r'(?is)<div[^>]*class="[^"]*wiki[^"]*"[^>]*>(.*?)</div>', html)
    if m and len(m.group(1)) > 80:
        return strip_tags(m.group(1))
    m = re.search(
        r'(?is)<div[^>]*id="content"[^>]*>(.*?)</div>\s*<div[^>]*id="sidebar"',
        html,
    )
    if m:
        return strip_tags(m.group(1))
    return strip_tags(html)


def _label_regexes():
    # longest first
    labels = sorted(KNOWN_LABELS, key=len, reverse=True)
    alts = "|".join(re.escape(x) for x in labels)
    return re.compile(rf"(?im)^(?:{alts})\s*:\s*(.*)$")


def parse_labeled_fields(text: str) -> dict[str, str]:
    """Split ticket body on known labels; values may span multiple lines."""
    text = _clean(text)
    labels = sorted(KNOWN_LABELS, key=len, reverse=True)
    pattern = re.compile(
        r"(?im)^(" + "|".join(re.escape(x) for x in labels) + r")\s*:\s*(.*)$"
    )

    matches = list(pattern.finditer(text))
    fields: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        # normalize key casing to canonical
        for lab in KNOWN_LABELS:
            if lab.lower() == key.lower():
                key = lab
                break
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        first = (m.group(2) or "").strip()
        rest = text[start:end].strip()
        value = first
        if rest:
            value = (first + "\n" + rest).strip() if first else rest
        # if key already exists (duplicate), keep longer
        if key not in fields or len(value) > len(fields[key]):
            fields[key] = value.strip()
    return fields


def get_exact(fields: dict[str, str], *names: str) -> str:
    lowered = {k.lower(): v for k, v in fields.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()].strip()
    return ""


def format_features(raw: str) -> str:
    if not raw:
        return ""
    lines = []
    for line in re.split(r"[\n•]+", raw):
        line = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
        line = line.strip(" -•\t")
        if line and len(line) > 1:
            lines.append(line)
    # also split on commas if single long line and few newlines
    if len(lines) <= 1 and "," in raw and "\n" not in raw.strip():
        lines = [p.strip() for p in raw.split(",") if p.strip()]
    out = []
    for i, feat in enumerate(lines, 1):
        out.append(f"{i}. {feat}")
    return "\n".join(out)


CATEGORY_KEYS = [
    "Device Type",
    "Vertical",
    "Use Cases",
    "Open Software Platform",
    "Intel Technologies",
    "Intel Processors",
    "Intel Graphics",
    "Geo Availability",
    "Edge Feature",
    "AI Edge System Sizing",
    "Target Audience",
]


def build_categories(fields: dict[str, str]) -> str:
    # Prefer block under categories header; else assemble section keys
    block = get_exact(
        fields,
        "Application Categories & Sub-Categories",
        "Product Categories & Sub-Categories",
        "System Categories & Sub-Categories",
        "Categories & Sub-Categories",
    )
    lines = []
    if block:
        # block may already contain Vertical: ... lines
        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[A-Za-z].+:\s*.+", line):
                lines.append(line)
            elif lines:
                # continuation of previous value
                lines[-1] = lines[-1] + " " + line
            else:
                lines.append(line)

    # Always merge known category keys if present as standalone fields
    for key in CATEGORY_KEYS:
        val = get_exact(fields, key)
        if not val:
            continue
        # take first line / trim if value contains nested labels
        val = val.split("\n")[0].strip()
        entry = f"{key}: {val}"
        # replace if key already in lines
        replaced = False
        for i, existing in enumerate(lines):
            if existing.lower().startswith(key.lower() + ":"):
                lines[i] = entry
                replaced = True
                break
        if not replaced:
            lines.append(entry)

    # dedupe
    seen = set()
    out = []
    for line in lines:
        key = line.split(":", 1)[0].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


def extract_emails(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s<>\")\]]+", text or "")
    out, seen = [], set()
    for u in urls:
        u = u.rstrip(".,);]")
        if any(x in u for x in ("websupport.onsumaye.com", "sharepoint.com", "intel.sharepoint")):
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def detect_product_type(subject: str, body: str, fields: dict) -> str:
    blob = f"{subject}\n{body}".lower()
    if "systems partner showcase" in blob or "system partner showcase" in blob:
        return "system"
    if get_exact(fields, "Product Name") and not get_exact(fields, "Application Name"):
        return "system"
    if "application partner showcase" in blob:
        return "application"
    return "application"


def map_ticket(ticket_id: int, subject: str, body: str) -> dict:
    fields = parse_labeled_fields(body)

    product_name = get_exact(
        fields, "Application Name", "Product Name", "System Name"
    ) or subject
    for prefix in (
        "Application Partner Showcase",
        "System Partner Showcase",
        "Systems Partner Showcase",
        "Partner Spotlight",
        "Website Assistance",
    ):
        product_name = re.sub(
            rf"^{re.escape(prefix)}\s*[:\-–#\d\s]*",
            "",
            product_name,
            flags=re.I,
        ).strip()

    partner_name = get_exact(
        fields, "Partner Display Name", "Partner Name", "Company Name"
    )
    partner_dropdown = partner_name

    short_desc = get_exact(
        fields,
        "Application Short Description",
        "Product Short Description",
        "System Short Description",
        "Short Description",
    )
    full_desc = get_exact(
        fields,
        "Application Description",
        "Product Description",
        "System Description",
    )
    # Do NOT fall back to generic "Description" if it might be ambiguous

    features = format_features(
        get_exact(
            fields,
            "Application Features",
            "Product Features",
            "System Features",
            "Features",
        )
    )
    categories = build_categories(fields)

    contact_raw = get_exact(fields, "Partner Contact", "Contact")
    resources_raw = get_exact(
        fields,
        "Application Resources",
        "Product Resources",
        "System Resources",
        "Resources",
    )
    website = get_exact(fields, "Partner Website", "Website")

    emails = extract_emails(contact_raw) or extract_emails(body)
    contact_urls = extract_urls(contact_raw) + extract_urls(website)
    resource_urls = extract_urls(resources_raw)
    # Prefer non-calendly resource home pages when available
    if website and not resource_urls:
        resource_urls = extract_urls(website)

    contact_parts = []
    for e in emails[:2]:
        contact_parts.append(f"mailto:{e}")
    for u in contact_urls[:2]:
        if u not in contact_parts:
            contact_parts.append(u)
    # If only mailto, try add first resource domain as partner site
    if contact_parts and all(p.startswith("mailto:") for p in contact_parts) and resource_urls:
        contact_parts.append(resource_urls[0])

    product_type = detect_product_type(subject, body, fields)
    title = get_exact(fields, "Page Title", "Meta Title") or product_name
    meta_desc = get_exact(fields, "Meta Description")
    keywords = get_exact(fields, "Meta Keywords", "Keywords")

    return {
        "ticket_id": ticket_id,
        "ticket_number": ticket_id,
        "subject": subject,
        "enabled": True,
        "partner_name": partner_name,
        "partner_dropdown_label": partner_dropdown,
        "product_name": product_name,
        "product_type": product_type,
        "search_term": product_name,
        "expected_title": title,
        "expected_short_description": short_desc,
        "expected_description": full_desc or short_desc,
        "expected_meta_description": meta_desc,
        "expected_keywords": keywords,
        "expected_features": features,
        "expected_categories": categories,
        "category_subcategory": categories,
        "expected_contact_url": "; ".join(contact_parts),
        "expected_resource_url": "; ".join(resource_urls[:3]),
        "validate_pdf": False,
        "expected_pdf_text": "",
        "field_keys": list(fields.keys()),
    }


COLUMNS = [
    "enabled",
    "test_id",
    "ticket_number",
    "partner_name",
    "partner_dropdown_label",
    "product_name",
    "product_type",
    "search_term",
    "expected_title",
    "expected_short_description",
    "expected_description",
    "expected_meta_description",
    "expected_keywords",
    "expected_features",
    "expected_categories",
    "category_subcategory",
    "expected_contact_url",
    "expected_resource_url",
    "validate_pdf",
    "expected_pdf_text",
]


def main():
    if not USERNAME or not PASSWORD:
        raise SystemExit(
            "Set WEBSUPPORT_USER and WEBSUPPORT_PASS environment variables before running."
        )
    opener = build_opener(HTTPCookieProcessor())
    print("Logging in...")
    login(opener)

    mapped_rows = []
    for idx, tid in enumerate(TICKET_IDS, 1):
        url = f"{BASE}/issues/{tid}"
        print(f"[{idx}/{len(TICKET_IDS)}] {tid}")
        html = _http_get(opener, url)
        subject = extract_subject(html)
        body = extract_description_html(html)
        row = map_ticket(tid, subject, body)
        row["test_id"] = f"PS-{idx:03d}"
        row["ticket_url"] = url
        mapped_rows.append(row)
        print(
            f"  {row['test_id']} | {row['partner_name']} | {row['product_name']} | "
            f"{row['product_type']} | cats={bool(row['category_subcategory'])} | "
            f"desc_len={len(row['expected_description'])}"
        )

    # Persist debug JSON
    OUT_JSON.write_text(json.dumps(mapped_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    excel_rows = []
    for row in mapped_rows:
        excel_rows.append({col: row.get(col, "") for col in COLUMNS})

    df = pd.DataFrame(excel_rows, columns=COLUMNS)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PartnerProducts", index=False)

    print(f"Wrote {OUT_XLSX} with {len(df)} rows")
    print(df[["test_id", "partner_name", "product_name", "product_type"]].to_string(index=False))


if __name__ == "__main__":
    main()
