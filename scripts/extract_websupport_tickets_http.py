"""HTTP login + scrape Redmine/WebSupport tickets into JSON for Excel mapping."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "testdata" / "_ticket_extract.json"

import os

BASE = "https://websupport.onsumaye.com"
USERNAME = os.environ.get("WEBSUPPORT_USER", "")
PASSWORD = os.environ.get("WEBSUPPORT_PASS", "")

TICKET_IDS = [
    25102, 25122, 25123, 25103, 25101, 25104, 25116, 25106,
    25107, 25108, 25109, 25110, 25111, 25112, 25113, 25114,
]


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False
        self._in_h2 = False
        self.h2_texts: list[str] = []
        self._capture_desc = False
        self.desc_parts: list[str] = []
        self._in_wiki = False
        self.attrs: dict[str, str] = {}
        self._pending_label = ""

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "h2":
            self._in_h2 = True
        if tag == "div" and "wiki" in cls:
            self._in_wiki = True
        if tag == "div" and "description" in cls:
            self._capture_desc = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag == "h2":
            self._in_h2 = False
        if tag == "div" and self._in_wiki:
            self._in_wiki = False
        if tag == "div" and self._capture_desc:
            # keep capturing until nested closed roughly - flush later
            pass

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text + " "
        if self._in_h2:
            self.h2_texts.append(text)
        if self._in_wiki or self._capture_desc:
            self.desc_parts.append(text)
        self.parts.append(text)


def _clean(text: str) -> str:
    if not text:
        return ""
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"):
        text = text.replace(ch, " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _http_get(opener, url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (QA-Automation)"})
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _http_post(opener, url: str, data: dict) -> str:
    from urllib.parse import urlencode

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
    m = re.search(
        r'name="authenticity_token"[^>]*value="([^"]+)"',
        html,
    ) or re.search(r'value="([^"]+)"[^>]*name="authenticity_token"', html)
    if m:
        token = m.group(1)

    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "login": "Login",
    }
    if token:
        payload["authenticity_token"] = token

    html2 = _http_post(opener, f"{BASE}/login", payload)
    if 'name="username"' in html2 and "logout" not in html2.lower():
        # some redmine redirect then need check my/page
        check = _http_get(opener, f"{BASE}/my/page")
        if "login" in check.lower() and 'name="password"' in check:
            raise RuntimeError("Login failed")
    print("Login OK")


def strip_tags(html: str) -> str:
    # remove scripts/styles
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>", "\n", html)
    html = re.sub(r"(?is)</div>", "\n", html)
    html = re.sub(r"(?is)</li>", "\n", html)
    html = re.sub(r"(?is)</h[1-6]>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&#39;", "'", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n[ \t]+", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def extract_subject(html: str) -> str:
    m = re.search(r"<h2[^>]*>\s*(?:<[^>]+>\s*)*([^<]+)", html, re.I)
    if m:
        return _clean(m.group(1))
    m = re.search(r"<title>([^<]+)</title>", html, re.I)
    if m:
        t = m.group(1)
        t = re.sub(r"\s*-\s*Your Support Projects.*$", "", t).strip()
        return t
    return ""


def extract_description_html(html: str) -> str:
    # Prefer description wiki block
    m = re.search(
        r'(?is)<div[^>]*class="[^"]*description[^"]*"[^>]*>.*?<div[^>]*class="[^"]*wiki[^"]*"[^>]*>(.*?)</div>',
        html,
    )
    if m:
        return strip_tags(m.group(1))
    m = re.search(
        r'(?is)<div[^>]*class="[^"]*wiki[^"]*"[^>]*>(.*?)</div>',
        html,
    )
    if m and len(m.group(1)) > 80:
        return strip_tags(m.group(1))
    # fallback content
    m = re.search(r'(?is)<div[^>]*id="content"[^>]*>(.*?)</div>\s*<div[^>]*id="sidebar"', html)
    if m:
        return strip_tags(m.group(1))[:20000]
    return strip_tags(html)[:20000]


def parse_pairs(text: str) -> dict[str, str]:
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
        line = line.strip()
        if not line:
            if current_key is not None:
                current_vals.append("")
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9 /&\-()°®™]{1,70}?)\s*:\s*(.*)$", line)
        if m:
            flush()
            current_key = m.group(1).strip()
            rest = m.group(2).strip()
            current_vals = [rest] if rest else []
        elif current_key is not None:
            current_vals.append(line)
    flush()
    return pairs


def find_key(pairs: dict[str, str], *candidates: str) -> str:
    lowered = {k.lower().strip(): v for k, v in pairs.items()}
    for cand in candidates:
        c = cand.lower()
        if c in lowered:
            return lowered[c]
        for k, v in lowered.items():
            if c == k or c in k:
                return v
    return ""


def extract_emails(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s<>\")\]]+", text or "")
    out, seen = [], set()
    for u in urls:
        u = u.rstrip(".,);]")
        if "websupport.onsumaye.com" in u or "redmine" in u:
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def detect_product_type(subject: str, body: str) -> str:
    blob = f"{subject}\n{body}".lower()
    if "system partner showcase" in blob:
        return "system"
    if "application partner showcase" in blob:
        return "application"
    if re.search(r"\bsystem\b", subject.lower()):
        return "system"
    return "application"


def map_ticket(ticket_id: int, subject: str, body: str) -> dict:
    body = _clean(body)
    pairs = parse_pairs(body)

    product_name = find_key(
        pairs,
        "Application Name",
        "Product Name",
        "System Name",
        "Solution Name",
    )
    if not product_name:
        product_name = subject
        for prefix in (
            "Application Partner Showcase",
            "System Partner Showcase",
            "Partner Spotlight",
        ):
            product_name = re.sub(
                rf"^{re.escape(prefix)}\s*[:\-–]\s*",
                "",
                product_name,
                flags=re.I,
            ).strip()

    partner_name = find_key(
        pairs,
        "Partner Display Name",
        "Partner Name",
        "Company Name",
        "Partner",
        "Company",
    )
    partner_dropdown = (
        find_key(
            pairs,
            "Partner Dropdown Label",
            "Filter By Partners",
            "Partner Dropdown",
            "Partner Display Name",
            "Partner Name",
        )
        or partner_name
    )

    short_desc = find_key(
        pairs,
        "Short Description",
        "Application Short Description",
        "System Short Description",
    )
    full_desc = find_key(
        pairs,
        "Description",
        "Application Description",
        "System Description",
        "Full Description",
        "Product Description",
    )
    # if Description key matched short incorrectly empty first values
    features = find_key(
        pairs,
        "Application Features",
        "System Features",
        "Features",
        "Key Features",
    )
    categories = find_key(
        pairs,
        "Application Categories & Sub-Categories",
        "Application Categories and Sub-Categories",
        "System Categories & Sub-Categories",
        "Categories & Sub-Categories",
        "Categories and Sub-Categories",
        "Application Categories",
        "Categories",
    )
    meta_desc = find_key(pairs, "Meta Description", "SEO Description")
    keywords = find_key(pairs, "Meta Keywords", "Keywords", "Meta Keyword")
    title = (
        find_key(pairs, "Page Title", "Meta Title", "Detail Title", "Application Name", "Product Name")
        or product_name
    )

    contact_section = find_key(
        pairs,
        "Partner Contact",
        "Contact Email",
        "Contact Link",
        "Contact",
        "Partner Contact Email",
    )
    resources = find_key(
        pairs,
        "Application Resources",
        "System Resources",
        "Resources",
        "Resource URL",
        "Resource Links",
    )
    website = find_key(pairs, "Partner Website", "Website", "Company Website", "Partner URL")

    emails = extract_emails(contact_section) or extract_emails(body)
    urls_contact = extract_urls(contact_section) + extract_urls(website)
    resource_urls = extract_urls(resources) or extract_urls(website)

    contact_parts = []
    for e in emails[:2]:
        contact_parts.append(f"mailto:{e}")
    for u in urls_contact[:2]:
        if u not in contact_parts:
            contact_parts.append(u)

    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "raw_pair_keys": list(pairs.keys()),
        "partner_name": partner_name,
        "partner_dropdown_label": partner_dropdown,
        "product_name": product_name,
        "product_type": detect_product_type(subject, body),
        "search_term": product_name,
        "expected_title": title,
        "expected_short_description": short_desc,
        "expected_description": full_desc,
        "expected_meta_description": meta_desc,
        "expected_keywords": keywords,
        "expected_features": features,
        "expected_categories": categories,
        "category_subcategory": categories,
        "expected_contact_url": "; ".join(contact_parts),
        "expected_resource_url": "; ".join(resource_urls[:3]),
        "body_preview": body[:2000],
    }


def main():
    opener = build_opener(HTTPCookieProcessor())
    login(opener)
    results = []
    for tid in TICKET_IDS:
        url = f"{BASE}/issues/{tid}"
        print(f"Fetching {tid}...")
        try:
            html = _http_get(opener, url)
            if 'name="password"' in html and "logout" not in html.lower():
                raise RuntimeError("Session expired / not authenticated")
            subject = extract_subject(html)
            body = extract_description_html(html)
            mapped = map_ticket(tid, subject, body)
            mapped["url"] = url
            results.append(mapped)
            print(
                f"  OK partner={mapped['partner_name']!r} product={mapped['product_name']!r} "
                f"keys={mapped['raw_pair_keys'][:8]}"
            )
        except Exception as exc:
            print(f"  FAIL {tid}: {exc}")
            results.append({"ticket_id": tid, "error": str(exc)})

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
