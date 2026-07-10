from playwright.sync_api import Page

import re

from utilities.constants import (
    CATEGORIES_SECTION_SELECTORS,
    CONTACT_LINK_SELECTORS,
    FEATURES_SECTION_SELECTORS,
    RELATED_PRODUCTS_SELECTORS,
    RESOURCES_SECTION_SELECTORS,
    THUMBNAIL_SELECTORS,
)
from utilities.logger import get_logger
from utilities.text_parser import texts_match

logger = get_logger(__name__)


class DetailValidator:
    """Validates Product Detail page (steps 15-26)."""

    def __init__(self, page: Page):
        self.page = page

    def validate_thumbnail(self, product_name=None):
        for selector in THUMBNAIL_SELECTORS:
            img = self.page.locator(selector).first
            if img.count() == 0 or not img.is_visible(timeout=3000):
                continue
            nw = img.evaluate("el => el.naturalWidth")
            if nw > 0:
                alt = img.get_attribute("alt") or ""
                if product_name and product_name.lower() not in alt.lower():
                    continue
                return True, "Thumbnail image loaded", {
                    "alt": alt,
                    "src": img.get_attribute("src"),
                }
        return False, "Thumbnail image not found or failed to load", {}

    def validate_full_description(self, expected_snippet=""):
        meta = self.page.locator("meta[name='description']").first
        desc = meta.get_attribute("content") if meta.count() else ""
        body = self.page.locator("main, [class*='product' i], .container").first
        if body.count():
            body_text = body.inner_text(timeout=8000)
        else:
            body_text = ""
        full = f"{desc} {body_text}".strip()
        if not full:
            return False, "Product description is empty", full
        if expected_snippet and not texts_match(expected_snippet, full, min_keyword_ratio=0.35):
            keywords = [
                w.strip(".,;:")
                for w in expected_snippet.replace(",", " ").split()
                if len(w.strip(".,;:")) > 3
            ]
            matched = sum(1 for w in keywords if w.lower() in full.lower())
            min_match = max(3, len(keywords) // 4) if len(keywords) > 12 else max(2, len(keywords) // 2)
            if matched < min_match:
                return (
                    False,
                    f"Description snippet missing: {expected_snippet}",
                    full[:300],
                )
        return True, "Product description validated", full[:300]

    def validate_partner_contact_link(self, expected_fragment=""):
        """Validate partner contact — mailto:, https URL, or domain fragment."""
        from utilities.text_parser import parse_expected_contact_fragments

        if isinstance(expected_fragment, (list, tuple)):
            expected_fragments = [str(f).strip() for f in expected_fragment if str(f).strip()]
        else:
            expected_fragments = parse_expected_contact_fragments(expected_fragment)

        contact_links = self._collect_contact_candidates()
        page_haystack = self._contact_page_haystack()

        if not contact_links and not page_haystack:
            info = {"matched": [], "missing": expected_fragments, "links": []}
            return False, "Partner contact link not found or invalid", info

        if not expected_fragments:
            link = contact_links[0] if contact_links else {"text": "contact", "href": ""}
            return (
                True,
                f"Partner contact found: {link.get('text') or link.get('href')}",
                {"matched": ["any"], "missing": [], "links": contact_links},
            )

        matched = []
        missing = []
        for fragment in expected_fragments:
            if self._fragment_on_contact_page(fragment, contact_links, page_haystack):
                matched.append(fragment)
            else:
                missing.append(fragment)

        info = {"matched": matched, "missing": missing, "links": contact_links}

        if missing:
            on_page = [
                link.get("resolved") or link.get("href") or link.get("text")
                for link in contact_links[:5]
            ]
            return (
                False,
                (
                    f"Partner contact mismatch ({len(matched)}/{len(expected_fragments)} matched). "
                    f"Missing: {missing}. On page: {on_page}"
                ),
                info,
            )

        primary = contact_links[0] if contact_links else {}
        return (
            True,
            (
                f"Partner contact OK ({len(matched)} fragment(s)): "
                f"{primary.get('resolved') or primary.get('text') or primary.get('href')}"
            ),
            info,
        )

    def _collect_contact_candidates(self):
        """Collect contact controls including javascript:void(0) + onclick mailto."""
        candidates = []
        seen = set()

        harvested = self.page.evaluate(
            """() => {
                const out = [];
                const nodes = document.querySelectorAll(
                    'a, button, [role="button"], [role="link"], [class*="contact" i] *'
                );
                for (const el of nodes) {
                    const href = el.getAttribute('href') || '';
                    const onclick = el.getAttribute('onclick') || '';
                    const text = (el.textContent || '').trim().slice(0, 200);
                    const attrs = Array.from(el.attributes)
                        .map(a => `${a.name}=${a.value}`)
                        .join(' ');
                    const hay = `${href} ${onclick} ${text} ${attrs}`.toLowerCase();
                    if (!/contact|mailto|@|partner/i.test(hay)) continue;

                    const mailtoMatch =
                        hay.match(/mailto:[^\\s'";,)]+/i) ||
                        attrs.match(/mailto:[^\\s'";,)]+/i);
                    const emails = [
                        ...new Set(
                            (hay.match(/[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}/gi) || [])
                        ),
                    ];

                    let resolved = href;
                    if (mailtoMatch) {
                        resolved = mailtoMatch[0];
                    } else if (emails.length === 1) {
                        resolved = `mailto:${emails[0]}`;
                    }

                    out.push({
                        href,
                        onclick,
                        text,
                        attrs: attrs.slice(0, 400),
                        mailto: mailtoMatch ? mailtoMatch[0] : '',
                        emails,
                        resolved,
                    });
                }
                return out;
            }"""
        )

        for item in harvested or []:
            key = (item.get("href", ""), item.get("text", "")[:60], item.get("mailto", ""))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(item)

        for selector in CONTACT_LINK_SELECTORS:
            links = self.page.locator(selector)
            for i in range(min(links.count(), 20)):
                link = links.nth(i)
                try:
                    text = link.inner_text(timeout=2000).strip()
                    href = link.get_attribute("href") or ""
                    onclick = link.get_attribute("onclick") or ""
                except Exception:
                    continue
                if not self._is_partner_contact_link(href, text, onclick):
                    continue
                hay = f"{href} {onclick} {text}".lower()
                emails = re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", hay, re.I)
                mailto = re.search(r"mailto:[^\s'\";,)]+", hay, re.I)
                resolved = mailto.group(0) if mailto else (f"mailto:{emails[0]}" if len(emails) == 1 else href)
                key = (href, text[:60], resolved)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "href": href,
                        "onclick": onclick,
                        "text": text,
                        "attrs": "",
                        "mailto": mailto.group(0) if mailto else "",
                        "emails": emails,
                        "resolved": resolved,
                    }
                )

        return candidates

    def _contact_page_haystack(self):
        """HTML/text blob for contact section and mailto fallbacks."""
        parts = []
        for selector in (
            "[class*='contact' i]",
            "a:has-text('Contact')",
            "button:has-text('Contact')",
            "main",
        ):
            loc = self.page.locator(selector).first
            try:
                if loc.count():
                    parts.append(loc.inner_html(timeout=3000))
                    parts.append(loc.inner_text(timeout=2000))
            except Exception:
                continue
        try:
            parts.append(self.page.content())
        except Exception:
            pass
        return "\n".join(p for p in parts if p)

    def _fragment_on_contact_page(self, fragment, contact_links, page_haystack):
        if self._contact_matches_fragment("", "", fragment, page_haystack=page_haystack):
            return True
        return any(
            self._contact_matches_fragment(
                link.get("href", ""),
                link.get("text", ""),
                fragment,
                onclick=link.get("onclick", ""),
                attrs=link.get("attrs", ""),
                mailto=link.get("mailto", ""),
                emails=link.get("emails", []),
                resolved=link.get("resolved", ""),
            )
            for link in contact_links
        )

    @staticmethod
    def _is_partner_contact_link(href, text, onclick=""):
        href_l = (href or "").lower()
        text_l = (text or "").lower()
        onclick_l = (onclick or "").lower()
        blob = f"{href_l} {text_l} {onclick_l}"
        return (
            href_l.startswith("mailto:")
            or "contact" in href_l
            or "contact" in text_l
            or text_l.startswith("contact ")
            or "partner contact" in text_l
            or "mailto:" in onclick_l
            or ("@" in blob and "contact" in blob)
        )

    @staticmethod
    def _extract_email(fragment):
        frag = str(fragment or "").strip().lower()
        if frag.startswith("mailto:"):
            return frag.replace("mailto:", "").strip()
        if "@" in frag and not frag.startswith("http"):
            return frag
        return ""

    @staticmethod
    def _contact_matches_fragment(
        href,
        text,
        fragment,
        onclick="",
        attrs="",
        emails=None,
        mailto="",
        resolved="",
        page_haystack="",
    ):
        fragment = str(fragment or "").strip()
        if not fragment:
            return False

        href_l = (href or "").lower()
        text_l = (text or "").lower()
        frag_l = fragment.lower().strip()
        blob = " ".join(
            [
                href_l,
                text_l,
                (onclick or "").lower(),
                (attrs or "").lower(),
                (mailto or "").lower(),
                (resolved or "").lower(),
                (page_haystack or "").lower(),
            ]
        )
        if emails:
            blob += " " + " ".join(e.lower() for e in emails)

        expected_email = DetailValidator._extract_email(fragment)
        if expected_email:
            if expected_email in blob:
                return True
            if f"mailto:{expected_email}" in blob:
                return True
            return False

        frag_norm = frag_l.rstrip("/")
        bare = frag_norm.replace("https://", "").replace("http://", "")

        if frag_norm in blob:
            return True
        if bare and bare in blob:
            return True
        if href_l and frag_norm in href_l.rstrip("/"):
            return True
        return False

    def _verify_contact_link_reachable(self, href):
        """HEAD check for http(s) links only — skip mailto: and relative without base."""
        if not href or href.lower().startswith("mailto:"):
            return True
        target = href if href.startswith("http") else f"https://builders.intel.com{href}"
        if not href.startswith("http") and not href.startswith("/"):
            return True
        try:
            resp = self.page.request.head(target, timeout=15000)
            return resp.ok or resp.status in (301, 302, 303, 307, 308)
        except Exception:
            return True

    def _collect_features_section_text(self):
        page_text = self.page.inner_text("body")
        section_text = ""
        for selector in FEATURES_SECTION_SELECTORS:
            section = self.page.locator(selector).first
            if section.count() == 0:
                continue
            text = section.inner_text(timeout=5000).strip()
            if len(text) > 10:
                section_text = text
                break
        return section_text, page_text

    def validate_features_section(self, expected_features=None, strict=True):
        """Validate Features section against client-provided feature list."""
        from utilities.text_parser import feature_on_site, parse_expected_features

        if isinstance(expected_features, str):
            expected_features = parse_expected_features(expected_features)

        section_text, page_text = self._collect_features_section_text()
        haystack = section_text or page_text
        haystack_lower = haystack.lower()

        if "feature" not in haystack_lower and not section_text:
            info = {"found": [], "missing": list(expected_features or []), "section_text": ""}
            return False, "Features section not found", "", info

        if not expected_features:
            return True, "Features section present", section_text[:200], {
                "found": [],
                "missing": [],
                "section_text": section_text[:500],
            }

        found = []
        missing = []
        for feature in expected_features:
            if feature_on_site(feature, haystack):
                found.append(feature)
            else:
                missing.append(feature)

        info = {
            "found": found,
            "missing": missing,
            "section_text": section_text[:500],
        }

        if strict:
            if missing:
                msg = (
                    f"Strict feature validation failed: {len(missing)}/{len(expected_features)} "
                    f"missing from detail page.\n"
                    + "\n".join(f"  [FAIL] {item}" for item in missing)
                )
                return False, msg, section_text[:200], info
            msg = f"All {len(expected_features)} features found on detail page"
            return True, msg, section_text[:200], info

        # Legacy partial mode (kept for optional use)
        min_required = max(2, len(expected_features) // 2)
        if len(found) < min_required:
            return (
                False,
                f"Features missing ({len(found)}/{len(expected_features)}): {missing}",
                section_text[:200],
                info,
            )
        return (
            True,
            f"Features validated ({len(found)}/{len(expected_features)})",
            section_text[:200],
            info,
        )

    def validate_resources_section(self, expected_url=""):
        links = []
        for selector in RESOURCES_SECTION_SELECTORS:
            loc = self.page.locator(selector)
            for i in range(loc.count()):
                href = loc.nth(i).get_attribute("href") or ""
                text = loc.nth(i).inner_text(timeout=2000).strip()
                if href:
                    links.append({"text": text, "href": href})

        if expected_url:
            fragment = expected_url.lower().rstrip("/")
            for link in links:
                href = (link.get("href") or "").lower().rstrip("/")
                if fragment in href or href in fragment:
                    return True, f"Resource link matches client spec: {link['href']}", links
            # Also check anywhere on page (resource may be outside Resources block)
            body_hrefs = self.page.locator("a[href]").evaluate_all(
                "els => els.map(e => e.href).filter(Boolean)"
            )
            for href in body_hrefs:
                if fragment in href.lower():
                    return True, f"Resource link found on page: {href}", links
            if links:
                return (
                    False,
                    f"Expected resource URL not found: {expected_url}. Found: {[l['href'] for l in links[:3]]}",
                    links,
                )
            return False, f"Expected resource URL not found: {expected_url}", []

        if links:
            return True, f"Found {len(links)} resource link(s)", links
        return False, "No resource links found", []

    def validate_categories_section(self, expected_categories=None):
        expected_categories = expected_categories or []

        cat_elements = self.page.locator(
            ".cat-class, [class*='cat-class' i], [class*='categor' i] li, "
            "[class*='categor' i] span, [class*='categor' i] a, "
            "[class*='tag' i], [class*='badge' i]"
        )
        displayed = []
        for i in range(min(cat_elements.count(), 15)):
            text = cat_elements.nth(i).inner_text(timeout=1000).strip()
            if text and len(text) < 80:
                displayed.append(text)

        section_text = self.page.inner_text("body")
        if not displayed:
            # Product detail may show category tags inline
            for keyword in ["Manufacturing", "Retail", "Real-time", "Edge", "Vertical"]:
                if keyword.lower() in section_text.lower():
                    displayed.append(keyword)

        if not displayed:
            return False, "Categories section not found", []

        meaningful = [c for c in expected_categories if len(c.strip()) > 3]
        if meaningful:
            found = []
            missing = []
            for c in meaningful:
                if c.lower() in section_text.lower():
                    found.append(c)
                else:
                    words = [w for w in c.split() if len(w) > 3]
                    if words and sum(1 for w in words if w.lower() in section_text.lower()) >= len(words) // 2:
                        found.append(c)
                    else:
                        missing.append(c)
            min_required = max(2, len(meaningful) // 4)
            if len(found) < min_required:
                return (
                    False,
                    f"Categories not found ({len(found)}/{len(meaningful)}, need {min_required}): {missing[:5]}",
                    displayed[:5],
                )

        return True, f"Categories validated ({min(len(displayed), 5)} shown, {len(meaningful)} terms checked)", displayed[:5]

    def validate_related_products(self, partner_name):
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(1000)
        header = self.page.locator(RELATED_PRODUCTS_SELECTORS[0]).first
        if header.count() == 0:
            return False, "Related Products section not found", []

        section = header.locator("xpath=..")
        text = section.inner_text(timeout=5000)
        products = [
            line.strip() for line in text.split("\n")
            if line.strip() and line.strip() not in ("Related Products", "Hide")
        ]
        if not products:
            return False, "No related products displayed", []

        if partner_name:
            same_partner = [p for p in products if partner_name.split()[0].lower() in p.lower()]
            if same_partner:
                return True, f"Related products from partner: {len(same_partner)}", products
            return True, f"Related products displayed: {len(products)}", products

        return True, f"Related products displayed: {len(products)}", products
