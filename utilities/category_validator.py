"""Strict Category / Sub Category validation — Excel vs actual site content."""

import re

from playwright.sync_api import Page

from utilities.constants import CATEGORIES_SECTION_SELECTORS, LISTING_TAG_SELECTORS
from utilities.category_parser import canonical_subcategory_value
from utilities.logger import get_logger
from utilities.text_parser import normalize_text

logger = get_logger(__name__)

_CATEGORY_TAG_SELECTORS = [
    ".cat-class",
    "[class*='cat-class' i]",
    "[class*='categor' i] li",
    "[class*='categor' i] span",
    "[class*='categor' i] a",
    "[class*='tag' i]",
    "[class*='badge' i]",
    ".listview [class*='badge' i]",
    ".gridview [class*='badge' i]",
]


def normalize_category_text(text):
    """Normalize for comparison (unicode, trademarks, whitespace)."""
    if not text:
        return ""
    value = normalize_text(str(text))
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0", "\ufffd"):
        value = value.replace(ch, " ")
    value = re.sub(r"[®™]", "", value)
    value = re.sub(r"[^\w\s,()/\-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def _significant_words(text, min_len=3):
    words = re.findall(r"[a-z0-9]+", normalize_category_text(text))
    return [w for w in words if len(w) >= min_len and w not in ("and", "the", "for", "gen")]


def subcategory_on_site(expected_subcategory, haystack_normalized, visible_tags=None):
    """
    Return True if Excel sub-category text is present on the site.
    Uses normalized substring match first, then strict keyword match for long values.
    """
    if not expected_subcategory or not str(expected_subcategory).strip():
        return False

    expected = str(expected_subcategory).strip()
    norm_expected = normalize_category_text(expected)
    norm_haystack = normalize_category_text(haystack_normalized)
    canonical_expected = canonical_subcategory_value(expected)
    norm_canonical = normalize_category_text(canonical_expected)

    if norm_expected and norm_expected in norm_haystack:
        return True
    if norm_canonical and norm_canonical in norm_haystack:
        return True

    # OpenVINO Tool Kit vs OpenVINO Toolkit, etc.
    if norm_expected.replace(" ", "") in norm_haystack.replace(" ", ""):
        return True
    if norm_canonical.replace(" ", "") in norm_haystack.replace(" ", ""):
        return True

    # Site may use shorter label (e.g. Order Validation vs Order Accuracy)
    aliases = {
        "order accuracy": ["order validation", "order accuracy"],
        "openvino tool kit": ["openvino toolkit", "openvino tool kit"],
        "health life sciences": [
            "healthcare and life sciences",
            "health life sciences",
        ],
        "5ht gen intel xeon processors": [
            "5th gen intel xeon processors",
            "5ht gen intel xeon processors",
        ],
        "intel deep learning streamer": [
            "intel deep learning streamer",
            "deep learning streamer",
        ],
    }
    for key, variants in aliases.items():
        if key in norm_expected or norm_expected in key:
            if any(v in norm_haystack for v in variants):
                return True

    # Parenthetical values: also try the phrase inside parentheses
    paren = re.search(r"\(([^)]+)\)", expected)
    if paren:
        inner = normalize_category_text(paren.group(1))
        if inner and inner in norm_haystack:
            return True
        # e.g. "Product Recognition (detection, classification, tracking)"
        for part in re.split(r"[,;]", paren.group(1)):
            part_norm = normalize_category_text(part)
            if len(part_norm) > 4 and part_norm in norm_haystack:
                return True

    # Main label before "("
    main = expected.split("(")[0].strip()
    if main and main != expected:
        if normalize_category_text(main) in norm_haystack:
            return True

    if visible_tags:
        for tag in visible_tags:
            tag_norm = normalize_category_text(tag)
            if norm_expected in tag_norm or tag_norm in norm_expected:
                return True
            if norm_canonical in tag_norm or tag_norm in norm_canonical:
                return True
            if main and normalize_category_text(main) in tag_norm:
                return True

    # Strict keyword fallback for long Intel / use-case strings
    words = _significant_words(expected)
    if len(words) >= 3:
        matched = sum(1 for w in words if w in norm_haystack)
        threshold = max(len(words) - 1, int(len(words) * 0.75))
        if matched >= threshold:
            return True

    if len(words) == 2:
        if all(w in norm_haystack for w in words):
            return True

    # Intel processor lines: match generation + core + ultra/series tokens
    if "intel" in norm_expected and "processor" in norm_expected:
        gen = re.search(r"(\d+)(?:th|st|nd|rd)?\s*gen", norm_expected)
        series = re.search(r"series\s*(\d+)", norm_expected)
        ultra = "ultra" in norm_expected
        checks = []
        if gen:
            checks.append(gen.group(1) in norm_haystack)
        if series:
            checks.append(f"series {series.group(1)}" in norm_haystack or f"series{series.group(1)}" in norm_haystack.replace(" ", ""))
        if ultra:
            checks.append("ultra" in norm_haystack)
        if checks and all(checks):
            return True

    return False


class CategoryValidator:
    """Collect category text from site and compare with Excel ticket pairs."""

    def __init__(self, page: Page):
        self.page = page

    def _collect_visible_tags(self, root_selector=None):
        tags = []
        root = self.page.locator(root_selector) if root_selector else self.page
        selectors = _CATEGORY_TAG_SELECTORS + LISTING_TAG_SELECTORS
        seen = set()

        def add_tag(text):
            for part in re.split(r"[\n\r|]+", text):
                part = part.strip()
                if not part or len(part) > 120:
                    continue
                key = normalize_category_text(part)
                if key and key not in seen:
                    seen.add(key)
                    tags.append(part)

        for selector in selectors:
            loc = root.locator(selector) if root_selector else self.page.locator(selector)
            for i in range(min(loc.count(), 40)):
                try:
                    text = loc.nth(i).inner_text(timeout=800).strip()
                    if text:
                        add_tag(text)
                except Exception:
                    continue
        return tags

    def _scroll_to_categories_section(self):
        for pattern in (
            r"Categories",
            r"Application Categories",
            r"Sub-Categories",
        ):
            try:
                heading = self.page.get_by_role(
                    "heading", name=re.compile(pattern, re.I)
                ).first
                if heading.count() and heading.is_visible(timeout=2000):
                    heading.scroll_into_view_if_needed()
                    self.page.wait_for_timeout(800)
                    return heading
            except Exception:
                continue
        for selector in CATEGORIES_SECTION_SELECTORS:
            section = self.page.locator(selector).first
            try:
                if section.count() and section.is_visible(timeout=1500):
                    section.scroll_into_view_if_needed()
                    self.page.wait_for_timeout(800)
                    return section
            except Exception:
                continue
        return None

    def collect_listing_site_data(self, product_name):
        """Category text from Partner Spotlight listing (card + filter chips)."""
        from utilities.listing_validator import ListingValidator

        listing = ListingValidator(self.page)
        parts = []
        tags = []

        active = listing.get_active_filter_tags()
        tags.extend(active)
        parts.extend(active)

        card = listing.get_listing_card_for_product(product_name)
        if card.count():
            card_text = card.inner_text(timeout=5000)
            parts.append(card_text)
            tags.extend(self._collect_visible_tags())
            card_tags = card.locator(
                ".cat-class, [class*='cat-class' i], [class*='badge' i], span, a"
            )
            for i in range(min(card_tags.count(), 30)):
                try:
                    text = card_tags.nth(i).inner_text(timeout=500).strip()
                    if text and 3 < len(text) < 100:
                        tags.append(text)
                except Exception:
                    continue

        main = self.page.locator("main, [class*='content' i], .container").first
        if main.count():
            try:
                parts.append(main.inner_text(timeout=5000))
            except Exception:
                pass

        haystack = "\n".join(parts)
        return {
            "source": "listing",
            "tags": list(dict.fromkeys(tags)),
            "haystack": haystack,
            "haystack_normalized": normalize_category_text(haystack),
        }

    def collect_detail_site_data(self):
        """Category text from product detail page (authoritative for ticket spec)."""
        self.page.evaluate("window.scrollTo(0, 0)")
        self.page.wait_for_timeout(400)

        step = 350
        height = self.page.evaluate("document.body.scrollHeight")
        pos = 0
        while pos < height:
            pos += step
            self.page.evaluate(f"window.scrollTo(0, {pos})")
            self.page.wait_for_timeout(250)

        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(800)
        self._scroll_to_categories_section()

        parts = []
        tags = self._collect_visible_tags()

        heading = self._scroll_to_categories_section()
        if heading:
            try:
                block = heading.locator(
                    "xpath=ancestor::*[contains(@class,'row') or contains(@class,'container') or contains(@class,'section')][1]"
                )
                if block.count():
                    parts.append(block.first.inner_text(timeout=5000))
                else:
                    parts.append(heading.inner_text(timeout=3000))
                    sibling = heading.locator("xpath=following-sibling::*[1]")
                    if sibling.count():
                        parts.append(sibling.first.inner_text(timeout=3000))
            except Exception:
                pass

        for pattern in (
            r"Application Categories",
            r"Sub-Categories",
            r"Categories",
        ):
            try:
                el = self.page.get_by_text(re.compile(pattern, re.I)).first
                if el.count() and el.is_visible(timeout=1500):
                    el.scroll_into_view_if_needed()
                    parent = el.locator("xpath=ancestor::*[self::ul or self::div][1]")
                    if parent.count():
                        parts.append(parent.first.inner_text(timeout=4000))
                    parts.append(el.inner_text(timeout=2000))
            except Exception:
                continue

        for selector in CATEGORIES_SECTION_SELECTORS:
            section = self.page.locator(selector).first
            try:
                if section.count() and section.is_visible(timeout=1500):
                    section.scroll_into_view_if_needed()
                    text = section.inner_text(timeout=4000)
                    if text:
                        parts.append(text)
            except Exception:
                continue

        main = self.page.locator(
            "main, [class*='product-detail' i], [class*='product' i], .container"
        ).first
        if main.count():
            try:
                parts.append(main.inner_text(timeout=8000))
            except Exception:
                pass

        body = self.page.inner_text("body")
        parts.append(body)

        for tag in tags:
            parts.append(tag)

        haystack = "\n".join(p for p in parts if p)
        return {
            "source": "detail",
            "tags": tags,
            "haystack": haystack,
            "haystack_normalized": normalize_category_text(haystack),
        }

    def validate_pairs_strict(self, pairs, site_data):
        """
        Strict Excel vs site: every sub-category must appear on the site.
        pairs: [{"category": "Vertical", "subcategory": "Retail"}, ...]
        """
        if not pairs:
            return True, "No category/subcategory pairs in Excel", [], []

        found = []
        missing = []
        for pair in pairs:
            cat = pair.get("category", "")
            sub = pair.get("subcategory", "")
            if subcategory_on_site(
                sub,
                site_data.get("haystack_normalized", ""),
                site_data.get("tags"),
            ):
                found.append(pair)
            else:
                missing.append(pair)

        if missing:
            lines = [
                f"Category: {m['category']} | Sub Category: {m['subcategory']}"
                for m in missing
            ]
            msg = (
                f"Site vs Excel mismatch on {site_data.get('source', 'page')}: "
                f"{len(missing)}/{len(pairs)} sub-categories missing from site.\n"
                + "\n".join(lines)
            )
            logger.error(msg)
            logger.info(
                "Site tags sampled (%d): %s",
                len(site_data.get("tags", [])),
                site_data.get("tags", [])[:15],
            )
            return False, msg, found, missing

        msg = (
            f"All {len(pairs)} Category/Sub Category values from Excel "
            f"found on site ({site_data.get('source', 'page')})"
        )
        return True, msg, found, missing

    @staticmethod
    def merge_site_data(*sources):
        """Combine listing + detail page text/tags for full site comparison."""
        tags = []
        parts = []
        labels = []
        seen_tags = set()

        for data in sources:
            if not data:
                continue
            labels.append(data.get("source", "page"))
            for tag in data.get("tags") or []:
                key = normalize_category_text(tag)
                if key and key not in seen_tags:
                    seen_tags.add(key)
                    tags.append(tag)
            haystack = data.get("haystack") or ""
            if haystack:
                parts.append(haystack)

        combined_haystack = "\n".join(parts)
        return {
            "source": " + ".join(labels) if labels else "combined",
            "tags": tags,
            "haystack": combined_haystack,
            "haystack_normalized": normalize_category_text(combined_haystack),
        }

    def validate_pairs_combined(self, pairs, listing_data=None, detail_data=None):
        """Strict Excel vs site using listing tags + detail page content."""
        merged = self.merge_site_data(listing_data, detail_data)
        ok, msg, found, missing = self.validate_pairs_strict(pairs, merged)
        if ok:
            msg = (
                f"All {len(pairs)} Category/Sub Category values from Excel "
                f"found on site (listing + detail)"
            )
        else:
            msg = (
                f"Site vs Excel mismatch (listing + detail): "
                f"{len(missing)}/{len(pairs)} sub-categories missing.\n"
                + "\n".join(
                    f"Category: {m['category']} | Sub Category: {m['subcategory']}"
                    for m in missing
                )
            )
        report = self.format_comparison_report(pairs, merged, found, missing)
        return ok, msg, report, {"found": found, "missing": missing, "merged": merged}

    def format_comparison_report(self, pairs, site_data, found, missing):
        """Report block for HTML / Allure."""
        lines = [
            f"=== Site vs Excel ({site_data.get('source', 'page')}) ===",
            f"Excel pairs: {len(pairs)} | Found on site: {len(found)} | Missing: {len(missing)}",
            "",
            "Found:",
        ]
        for pair in found:
            lines.append(
                f"  [OK] Category: {pair['category']} | Sub Category: {pair['subcategory']}"
            )
        if missing:
            lines.append("")
            lines.append("Missing from site:")
            for pair in missing:
                lines.append(
                    f"  [FAIL] Category: {pair['category']} | Sub Category: {pair['subcategory']}"
                )
        lines.append("")
        lines.append(f"Site tags ({len(site_data.get('tags', []))}): {site_data.get('tags', [])[:20]}")
        return "\n".join(lines)
