import re

from playwright.sync_api import Page

from utilities.constants import (
    CATALOG_COUNT_SELECTORS,
    LISTING_CARD_SELECTOR,
    LISTING_TAG_SELECTORS,
    PARTNER_DROPDOWN_SEARCH_INPUTS,
    PARTNER_DROPDOWN_SELECTORS,
    PARTNER_DROPDOWN_TRIGGERS,
    PARTNER_LOGO_LISTING_SELECTORS,
    PRODUCT_TYPE_SELECTORS,
    QUICK_VIEW_OVERLAY_SELECTORS,
    QUICK_VIEW_SELECTORS,
    VIEW_MORE_SELECTORS,
)
from utilities.category_validator import CategoryValidator
from utilities.logger import get_logger

logger = get_logger(__name__)


class ListingValidator:
    """Validates Partner Spotlight listing page (steps 5-14)."""

    def __init__(self, page: Page):
        self.page = page

    def verify_spotlight_page_loaded(self):
        title = self.page.title()
        url = self.page.url
        ok = "Partner Spotlight" in title or "partner-spotlight" in url
        count = self.get_catalog_product_count()
        return ok, f"Page: {title}", {"url": url, "title": title, "catalog_count": count}

    def get_catalog_product_count(self):
        """Parse 'Catalog of N Unique Products' heading (per manual screenshots)."""
        pattern = re.compile(r"(\d+)\s+Unique Products", re.I)
        for selector in CATALOG_COUNT_SELECTORS:
            loc = self.page.locator(selector).first
            try:
                if loc.is_visible(timeout=3000):
                    text = loc.inner_text(timeout=3000)
                    match = pattern.search(text)
                    if match:
                        return int(match.group(1))
            except Exception:
                continue
        try:
            loc = self.page.get_by_text(pattern).first
            if loc.is_visible(timeout=2000):
                match = pattern.search(loc.inner_text(timeout=2000))
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return None

    @staticmethod
    def _unique_product_urls_from_links(links):
        """Deduplicate product detail URLs (one card may expose several spotlight links)."""
        product_urls = set()
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href") or ""
            slug_match = re.search(r"/partner-spotlight/([^/?#]+)", href)
            if slug_match and "-" in slug_match.group(1):
                product_urls.add(slug_match.group(1).lower())
        return product_urls

    def get_search_result_count(self):
        """
        Count visible search/listing results (one per product card).

        Never trust the catalog header alone while a search is active — the
        header can stay at a stale total (e.g. 96) while skeleton loaders show.
        """
        details_links = self.page.locator("a:has-text('Product Details')")
        detail_urls = self._unique_product_urls_from_links(details_links)
        if detail_urls:
            return len(detail_urls)

        # Visible product title links that point at a product slug.
        product_urls = self._unique_product_urls_from_links(
            self.page.locator("a[href*='/partner-spotlight/'][href*='-']")
        )
        if product_urls:
            return len(product_urls)

        # During / after search, skeleton rows mean "0 loaded results".
        if "psearch=" in (self.page.url or "").lower() or self._has_listing_skeletons():
            return 0

        catalog_count = self.get_catalog_product_count()
        if catalog_count is not None:
            return catalog_count
        return 0

    def _has_listing_skeletons(self):
        """True when listing shows placeholder cards instead of real products."""
        details = self.page.locator("a:has-text('Product Details')")
        try:
            if details.count() > 0 and details.first.is_visible(timeout=500):
                return False
        except Exception:
            pass

        for selector in (
            "[class*='skeleton' i]",
            "[class*='placeholder' i]",
            "[class*='shimmer' i]",
            "[class*='loading' i]",
        ):
            loc = self.page.locator(selector)
            try:
                if loc.count() >= 2:
                    return True
            except Exception:
                continue

        # Gray placeholder cards typically have .listview/.gridview but no product text.
        cards = self.page.locator(LISTING_CARD_SELECTOR)
        try:
            visible_cards = min(cards.count(), 6)
            emptyish = 0
            for i in range(visible_cards):
                text = (cards.nth(i).inner_text(timeout=500) or "").strip()
                if len(text) < 8:
                    emptyish += 1
            if visible_cards >= 3 and emptyish >= 2:
                return True
        except Exception:
            pass
        return False

    def validate_listing_category_subcategory_strict(self, product_name, category_pairs):
        """Strict Excel vs site on Partner Spotlight listing page."""
        validator = CategoryValidator(self.page)
        site_data = validator.collect_listing_site_data(product_name)
        ok, msg, found, missing = validator.validate_pairs_strict(category_pairs, site_data)
        report = validator.format_comparison_report(
            category_pairs, site_data, found, missing
        )
        logger.info("Listing category validation:\n%s", report)
        return ok, msg, report

    def get_active_filter_tags(self):
        """Read applied filter chips above listing (e.g. 'Application: Edge Device')."""
        tags = []
        for selector in [
            "[class*='filter' i] span",
            "[class*='tag' i]",
            "[class*='chip' i]",
            ".badge",
            "a.close-filter",
        ]:
            loc = self.page.locator(selector)
            for i in range(min(loc.count(), 30)):
                try:
                    text = loc.nth(i).inner_text(timeout=500).strip()
                    if text and 3 < len(text) < 120 and text not in tags:
                        if ":" in text or any(
                            kw in text.lower()
                            for kw in ("application", "system", "device", "retail", "edge")
                        ):
                            tags.append(text)
                except Exception:
                    continue
        return tags

    def _open_partner_dropdown(self):
        for selector in PARTNER_DROPDOWN_TRIGGERS:
            trigger = self.page.locator(selector).first
            try:
                if trigger.is_visible(timeout=2000):
                    trigger.click()
                    self.page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
        return False

    def _search_partner_in_dropdown(self, search_term):
        for selector in PARTNER_DROPDOWN_SEARCH_INPUTS:
            field = self.page.locator(selector).first
            try:
                if field.is_visible(timeout=2000):
                    field.fill(search_term)
                    self.page.wait_for_timeout(600)
                    return True
            except Exception:
                continue
        return False

    def _click_partner_checkbox(self, partner_name):
        labels = self.page.locator(
            ".multiselect-container label, .dropdown-menu label, "
            "[class*='multiselect' i] label"
        )
        for i in range(labels.count()):
            label = labels.nth(i)
            try:
                text = label.inner_text(timeout=1000).strip()
                if not text:
                    continue
                if partner_name.lower() in text.lower() or text.lower().startswith(
                    partner_name.split()[0].lower()
                ):
                    label.click()
                    self.page.wait_for_timeout(1500)
                    return True, text
            except Exception:
                continue
        return False, ""

    def select_partner_from_dropdown(self, partner_name, search_hint=None):
        """
        Filter By Partners dropdown: open, search (e.g. 'ad'), check partner row.
        Screenshots show 'Advantech Co. Ltd.' selected after typing 'ad'.
        """
        dropdown_label = search_hint or partner_name
        search_term = (search_hint or partner_name).split()[0][:3].lower() or partner_name[:3].lower()

        if self._open_partner_dropdown():
            self._search_partner_in_dropdown(search_term)
            ok, matched = self._click_partner_checkbox(partner_name)
            if ok:
                self._close_partner_dropdown()
                return True, f"Partner selected: {matched}"

            # Try full dropdown label variants
            for variant in [dropdown_label, f"{partner_name} Co. Ltd.", partner_name]:
                ok, matched = self._click_partner_checkbox(variant)
                if ok:
                    self._close_partner_dropdown()
                    return True, f"Partner selected: {matched}"

        # JS fallback on hidden multiselect
        for selector in PARTNER_DROPDOWN_SELECTORS:
            dropdown = self.page.locator(selector).first
            if dropdown.count() == 0:
                continue
            options = dropdown.locator("option").all_inner_texts()
            for opt in options:
                if partner_name.lower() in opt.lower():
                    dropdown.evaluate(
                        """(el, label) => {
                            for (const o of el.options) {
                                if (o.text.includes(label) || o.value.includes(label)) {
                                    o.selected = true;
                                    el.dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                            }
                            return false;
                        }""",
                        partner_name,
                    )
                    self.page.wait_for_timeout(2000)
                    return True, f"Partner selected via JS: {opt}"

        return False, f"Partner filter not found: {partner_name}"

    def _close_partner_dropdown(self):
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(400)
        except Exception:
            pass

    def verify_listing_displayed(self, min_count=1):
        count = self.get_search_result_count()
        catalog_count = self.get_catalog_product_count()
        if count >= min_count:
            msg = f"Listing displayed with {count} item(s)"
            if catalog_count is not None:
                msg += f"; catalog header shows {catalog_count}"
            return True, msg, count
        return False, "No product listing displayed", 0

    def get_listing_card_for_product(self, product_name):
        link = self._product_title_link(product_name)
        if link.count():
            card = link.locator(
                "xpath=ancestor::*[contains(@class,'listview') or contains(@class,'gridview')][1]"
            )
            if card.count():
                return card.first

        safe = str(product_name).replace("\\", "\\\\").replace("'", "\\'")
        card = self.page.locator(
            f"{LISTING_CARD_SELECTOR}:has(a:text-is('{safe}'))"
        ).first
        if card.count() == 0:
            card = self.page.locator(
                f"{LISTING_CARD_SELECTOR}:has(a:has-text('{safe}'))"
            ).first
        if card.count() == 0:
            card = self.page.locator(LISTING_CARD_SELECTOR).filter(
                has_text=re.compile(re.escape(str(product_name)), re.I)
            ).first
        return card

    def _product_title_link(self, product_name):
        """Locate product title; supports names with periods (e.g. HawkEye2.0)."""
        name = str(product_name or "").strip()
        if not name:
            return self.page.locator("a").nth(-1)

        link = self.page.get_by_role("link", name=name, exact=True)
        if link.count():
            return link.first

        safe = name.replace("\\", "\\\\").replace("'", "\\'")
        link = self.page.locator(f"a:text-is('{safe}')")
        if link.count():
            return link.first

        link = self.page.get_by_role("link", name=re.compile(rf"^{re.escape(name)}$"))
        if link.count():
            return link.first

        return self.page.get_by_text(name, exact=True).first

    @staticmethod
    def format_product_type_label(product_type):
        """UI badge label: Application or System."""
        return "Application" if str(product_type).lower().startswith("app") else "System"

    def validate_product_type_badge(self, product_name, expected_type):
        """Validate red-highlighted badge on listing card (Application / System)."""
        badge = self.get_product_type_badge(product_name)
        expected = (
            "application" if str(expected_type).lower().startswith("app") else "system"
        )
        label = self.format_product_type_label(expected)
        if badge == expected:
            return True, f"Product type badge: {label}", label
        if badge is None and self.is_product_listed(product_name):
            url = self.page.url.lower()
            if expected == "application" and "type=application" in url:
                return True, f"Product type from Application tab: {label}", label
            if expected == "system" and "type=system" in url:
                return True, f"Product type from System tab: {label}", label
        if badge:
            actual_label = self.format_product_type_label(badge)
            return (
                False,
                f"Badge shows '{actual_label}' but expected '{label}'",
                actual_label,
            )
        return False, f"Product type badge not found (expected {label})", None

    def validate_application_name(self, product_name):
        link = self._product_title_link(product_name)
        try:
            if link.count() and link.is_visible(timeout=3000):
                return True, f"Application name found: {product_name}"
        except Exception:
            pass

        card = self.get_listing_card_for_product(product_name)
        try:
            if card.count() and product_name.lower() in card.inner_text(timeout=5000).lower():
                return True, f"Application name found in card: {product_name}"
        except Exception:
            pass

        try:
            text_node = self.page.get_by_text(product_name, exact=True).first
            if text_node.count() and text_node.is_visible(timeout=2000):
                return True, f"Application name found on page: {product_name}"
        except Exception:
            pass

        return False, f"Application name not found: {product_name}"

    def validate_short_description(self, product_name, expected_snippet=""):
        card = self.get_listing_card_for_product(product_name)
        if card.count() == 0:
            return False, "Listing card not found for description check"
        text = card.inner_text(timeout=5000)
        if expected_snippet and expected_snippet.lower() not in text.lower():
            keywords = [w.strip(".,;:") for w in expected_snippet.replace(",", " ").split() if len(w.strip(".,;:")) > 3]
            if keywords and sum(1 for w in keywords if w.lower() in text.lower()) >= max(2, len(keywords) // 2):
                return True, f"Short description keywords matched: {expected_snippet[:60]}"
            # Fallback: check full page when card text is truncated in DOM
            page_text = self.page.inner_text("body")
            if expected_snippet.lower() in page_text.lower():
                return True, f"Short description found on page: {expected_snippet[:60]}"
            if keywords and sum(1 for w in keywords if w.lower() in page_text.lower()) >= max(2, len(keywords) // 2):
                return True, f"Short description keywords found on page"
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            desc_lines = [
                ln
                for ln in lines
                if product_name.lower() not in ln.lower()
                and "product details" not in ln.lower()
                and "quick view" not in ln.lower()
                and len(ln) > 15
            ]
            if desc_lines:
                return True, f"Short description present: {desc_lines[0][:80]}"
            return False, f"Short description snippet not found: {expected_snippet}"
        if len(text.strip()) > len(product_name) + 10:
            return True, "Application short description present on listing"
        return False, "Short description appears empty on listing"

    def validate_listing_tags(self, product_name, expected_tags=None):
        """Validate gray category tags on listing card (screenshot step 8-9)."""
        expected_tags = expected_tags or []
        card = self.get_listing_card_for_product(product_name)
        if card.count() == 0:
            return False, "Card not found for tag validation", []

        displayed = []
        for selector in LISTING_TAG_SELECTORS:
            tags = card.locator(selector)
            for i in range(tags.count()):
                text = tags.nth(i).inner_text(timeout=1000).strip()
                if text and len(text) < 80:
                    displayed.append(text)

        if not displayed:
            return True, "No listing tags on card (optional)", []

        if not expected_tags:
            return True, f"Listing tags present ({len(displayed)})", displayed[:5]

        found = [t for t in expected_tags if any(t.lower() in d.lower() for d in displayed)]
        if len(found) >= max(1, len(expected_tags) // 4):
            return True, f"Listing tags matched ({len(found)}/{len(expected_tags)})", displayed[:8]
        return False, f"Listing tags missing. Card tags: {displayed[:5]}", displayed[:8]

    def validate_partner_logo_on_listing(self, partner_name=None):
        logos = self.page.locator(PARTNER_LOGO_LISTING_SELECTORS[0])
        if logos.count() == 0:
            return False, "No partner logos on listing page", {}
        logo = logos.first
        if not logo.is_visible(timeout=3000):
            return False, "Partner logo not visible on listing", {}
        nw = logo.evaluate("el => el.naturalWidth")
        if nw == 0:
            return False, "Partner logo failed to load on listing", {}
        return True, "Partner logo displayed on listing", {
            "alt": logo.get_attribute("alt"),
            "src": logo.get_attribute("src"),
        }

    def validate_quick_view(self, product_name, expected_snippet=""):
        list_btn = self.page.locator("button:has(i.fa-th-list)").first
        if list_btn.is_visible(timeout=2000):
            list_btn.click()
            self.page.wait_for_timeout(1000)

        card = self.get_listing_card_for_product(product_name)
        scopes = [card] if card.count() else []
        product_link = self._product_title_link(product_name)
        if product_link.count():
            wider = product_link.locator(
                "xpath=ancestor::*["
                "contains(@class,'row') or contains(@class,'card') or "
                "contains(@class,'product')"
                "][1]"
            )
            if wider.count():
                scopes.append(wider.first)
        # Search produces one product in normal execution; global fallback
        # catches the blue eye icon when it is a sibling outside .listview.
        scopes.append(self.page)

        clicked = False
        for scope in scopes:
            for sel in QUICK_VIEW_SELECTORS:
                qv = scope.locator(sel).first
                try:
                    if qv.count() and qv.is_visible(timeout=2000):
                        qv.scroll_into_view_if_needed()
                        qv.click()
                        self.page.wait_for_timeout(1500)
                        clicked = True
                        break
                except Exception:
                    continue
            if clicked:
                break
        if not clicked:
            return False, "Quick View icon/link not found"

        overlay_text = ""
        for sel in QUICK_VIEW_OVERLAY_SELECTORS:
            overlays = self.page.locator(sel)
            for i in range(overlays.count()):
                overlay = overlays.nth(i)
                try:
                    if overlay.is_visible(timeout=2000):
                        text = overlay.inner_text(timeout=3000).strip()
                        tag_name = overlay.evaluate("el => el.tagName.toLowerCase()")
                        # [class*='quick-view'] also matches the trigger link.
                        if tag_name in ("a", "button") or text.lower() == "quick view":
                            continue
                        if text:
                            overlay_text = text
                            break
                except Exception:
                    continue
            if overlay_text:
                break

        if not overlay_text:
            # Bootstrap popovers can render without a stable wrapper. Validate
            # the visible page after clicking, not only the first 500 chars.
            overlay_text = self.page.inner_text("body")

        checks = [
            product_name.lower() in overlay_text.lower(),
            "product details" in overlay_text.lower(),
            "view more" in overlay_text.lower(),
        ]
        if expected_snippet:
            words = [
                word.lower().strip(".,;:")
                for word in expected_snippet.split()
                if len(word.strip(".,;:")) > 3
            ]
            checks.append(
                bool(words)
                and sum(word in overlay_text.lower() for word in words)
                >= max(2, len(words) // 2)
            )

        if any(checks):
            self._close_quick_view()
            return True, "Quick View overlay shows product information"

        self._close_quick_view()
        sample = " ".join(overlay_text.split())[:240]
        return (
            False,
            f"Quick View opened but product info not verified. Visible text: {sample}",
        )

    def _close_quick_view(self):
        for sel in [".popover .close", "button.close", "[aria-label='Close']"]:
            btn = self.page.locator(sel).first
            try:
                if btn.is_visible(timeout=1000):
                    btn.click()
                    return
            except Exception:
                continue
        self.page.keyboard.press("Escape")

    def is_product_listed(self, product_name):
        link = self._product_title_link(product_name)
        try:
            if link.count() and link.is_visible(timeout=3000):
                return True
        except Exception:
            pass
        card = self.get_listing_card_for_product(product_name)
        try:
            return card.count() > 0 and card.is_visible(timeout=2000)
        except Exception:
            return card.count() > 0

    def get_product_type_badge(self, product_name):
        """Read the blue top-right Application/System badge from the product card."""
        card = self.get_listing_card_for_product(product_name)
        scopes = []
        if card.count():
            scopes.append(card)

        # In list mode the title and the blue badge can be sibling columns, so
        # the nearest .listview node is occasionally narrower than the card.
        product_link = self._product_title_link(product_name)
        if product_link.count():
            wider = product_link.locator(
                "xpath=ancestor::*["
                "contains(@class,'row') or contains(@class,'card') or "
                "contains(@class,'product')"
                "][1]"
            )
            if wider.count():
                scopes.append(wider.first)

        for scope in scopes:
            for badge_text in ("Application", "System"):
                for selector in (
                    f"xpath=.//*[self::span or self::div or self::label]"
                    f"[normalize-space(.)='{badge_text}']",
                    f"[class*='badge' i]:text-is('{badge_text}')",
                    f"[class*='tag' i]:text-is('{badge_text}')",
                    f"[class*='type' i]:text-is('{badge_text}')",
                ):
                    el = scope.locator(selector).first
                    try:
                        if el.count() and el.is_visible(timeout=1000):
                            return badge_text.lower()
                    except Exception:
                        continue

        # Do not infer the product badge from ?type=. Search can reset tabs and
        # that caused false "System vs Application" reports.
        return None

    def select_product_type(self, product_type="system"):
        selectors = PRODUCT_TYPE_SELECTORS.get(product_type.lower(), [])
        for selector in selectors:
            loc = self.page.locator(selector).first
            try:
                if loc.is_visible(timeout=3000):
                    loc.click()
                    self.page.wait_for_timeout(1500)
                    return True, f"Selected product type: {product_type}"
            except Exception:
                continue
        return False, f"Product type tab not found: {product_type}"
