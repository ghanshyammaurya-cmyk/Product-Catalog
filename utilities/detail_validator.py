from playwright.sync_api import Page

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
        for selector in CONTACT_LINK_SELECTORS:
            links = self.page.locator(selector)
            for i in range(links.count()):
                link = links.nth(i)
                text = link.inner_text(timeout=3000).strip()
                href = link.get_attribute("href") or ""
                is_contact = (
                    "contact" in text.lower()
                    or "contact" in href.lower()
                    or text.lower().startswith("contact ")
                )
                if not is_contact:
                    continue
                if expected_fragment and expected_fragment.lower() not in href.lower():
                    if expected_fragment.lower() not in text.lower():
                        continue
                target = href if href.startswith("http") else f"https://builders.intel.com{href}"
                if href.startswith("http") or href.startswith("/"):
                    resp = self.page.request.head(target, timeout=15000)
                    if resp.ok or resp.status in (301, 302, 303, 307, 308):
                        return True, f"Partner contact link OK: {text or href}", {
                            "text": text,
                            "href": href,
                        }
                return True, f"Partner contact control found: {text}", {"text": text, "href": href}
        return False, "Partner contact link not found or invalid", {}

    def validate_features_section(self, expected_features=None):
        """Validate Features section against client-provided feature list."""
        if isinstance(expected_features, str):
            from utilities.text_parser import parse_expected_features
            expected_features = parse_expected_features(expected_features)

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

        haystack = (section_text or page_text).lower()
        if "feature" not in haystack and not section_text:
            return False, "Features section not found", ""

        if not expected_features:
            return True, "Features section present", section_text[:200]

        found = []
        missing = []
        for feature in expected_features:
            keywords = [w for w in feature.replace("&", " ").split() if len(w) > 3]
            if feature.lower() in haystack:
                found.append(feature)
            elif keywords and sum(1 for w in keywords if w.lower() in haystack) >= max(1, len(keywords) // 2):
                found.append(feature)
            else:
                missing.append(feature)

        min_required = max(2, len(expected_features) // 2)
        if len(found) < min_required:
            return (
                False,
                f"Features missing ({len(found)}/{len(expected_features)}): {missing}",
                section_text[:200],
            )
        return True, f"Features validated ({len(found)}/{len(expected_features)})", section_text[:200]

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
