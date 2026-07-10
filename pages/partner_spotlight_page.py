from pages.base_page import BasePage
from utilities.config_reader import ConfigReader
from utilities.constants import PRODUCT_LINK_SELECTORS, PRODUCT_TITLE_SELECTORS
from utilities.listing_validator import ListingValidator
from utilities.logo_validator import LogoValidator


class PartnerSpotlightPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.spotlight_url = ConfigReader.get("partner_spotlight_url")
        self.listing = ListingValidator(page)
        self.logo_validator = LogoValidator(page)

    def open(self, product_type=None):
        url = self._spotlight_url_for_type(product_type) if product_type else self.spotlight_url
        self.navigate_to(url)
        self.accept_cookies_if_present()

    def open_for_product_type(self, product_type="system"):
        """Open Partner Spotlight on System or Application tab (?type=system|application)."""
        self.navigate_to(self._spotlight_url_for_type(product_type))
        self.accept_cookies_if_present()
        self.wait_for_page_load()

    @staticmethod
    def _spotlight_url_for_type(product_type):
        base = ConfigReader.get("partner_spotlight_url").split("?")[0]
        ptype = "application" if str(product_type).lower().startswith("app") else "system"
        return f"{base}?type={ptype}"

    def _load_listing_context(
        self,
        product_type,
        search_term="",
        partner_name=None,
        partner_dropdown_label=None,
        reapply_partner=False,
    ):
        if "partner-spotlight" in self.page.url.lower():
            self.listing.select_product_type(product_type)
        else:
            self.open_for_product_type(product_type)

        if reapply_partner and partner_name:
            self.select_partner(partner_dropdown_label or partner_name, search_hint=partner_name)
        if search_term:
            self.catalog_search(search_term)
        self.page.wait_for_timeout(1500)

    def _product_matches_listing(self, product_name, short_description=""):
        if not self.listing.is_product_listed(product_name):
            return False
        if short_description:
            ok, _ = self.listing.validate_short_description(product_name, short_description)
            return ok
        return True

    def resolve_product_type(
        self,
        product_name,
        search_term="",
        partner_name=None,
        partner_dropdown_label=None,
        short_description="",
    ):
        """
        Resolve product type from site listing badge (screenshot highlight):
        - If product is on Application tab → 'application'
        - Otherwise if on System tab → 'system'
        """
        # 1. Application tab first
        self._load_listing_context(
            "application", search_term, partner_name, partner_dropdown_label
        )
        if self._product_matches_listing(product_name, short_description):
            badge = self.listing.get_product_type_badge(product_name) or "application"
            resolved = "application"
            self.logger.info(
                "Product '%s' resolved as Application (badge: %s)",
                product_name,
                self.listing.format_product_type_label(badge),
            )
            return True, resolved

        # 2. System tab fallback
        self._load_listing_context(
            "system", search_term, partner_name, partner_dropdown_label
        )
        if self._product_matches_listing(product_name, short_description):
            badge = self.listing.get_product_type_badge(product_name) or "system"
            resolved = "system" if badge != "application" else "application"
            self.logger.info(
                "Product '%s' resolved as System (badge: %s)",
                product_name,
                self.listing.format_product_type_label(resolved),
            )
            return True, resolved

        return False, "system"

    def ensure_product_listing(
        self,
        product_name,
        search_term="",
        preferred_type="system",
        partner_name=None,
        partner_dropdown_label=None,
        short_description="",
    ):
        """Legacy wrapper — resolves type from site (Application first, else System)."""
        ok, resolved = self.resolve_product_type(
            product_name,
            search_term=search_term,
            partner_name=partner_name,
            partner_dropdown_label=partner_dropdown_label,
            short_description=short_description,
        )
        if ok and preferred_type:
            pref = str(preferred_type).lower()
            if pref.startswith("app") and resolved != "application":
                self.logger.warning(
                    "Excel product_type is '%s' but site listing is '%s'",
                    preferred_type,
                    resolved,
                )
            elif pref.startswith("sys") and resolved == "application":
                self.logger.warning(
                    "Excel product_type is '%s' but product badge is Application",
                    preferred_type,
                )
        return ok, resolved

    def select_product_type(self, product_type="system"):
        return self.listing.select_product_type(product_type)

    def select_partner(self, partner_name, search_hint=None):
        return self.listing.select_partner_from_dropdown(partner_name, search_hint=search_hint)

    def validate_listing_category_subcategory_strict(self, product_name, category_pairs):
        return self.listing.validate_listing_category_subcategory_strict(
            product_name, category_pairs
        )

    def verify_page_loaded(self):
        return self.listing.verify_spotlight_page_loaded()

    def search_products(self, term):
        self.catalog_search(term)
        return self.get_product_link_count()

    def get_product_link_count(self):
        return self.listing.get_search_result_count()

    def is_search_results_page(self, search_term=""):
        """True when Partner Spotlight in-page search is active (pSearch in URL)."""
        url = self.page.url.lower()
        if "psearch=" in url:
            return True
        term = (search_term or "").strip().lower()
        if term and term in url:
            return True
        if term and term in (self.page.url or ""):
            return True
        return False

    def validate_views_on_search_results(self, search_term="", product_name=""):
        """
        Client UI: grid/list toggle icons appear after searching by product name.
        Ensures search context, then validates both views and optional product card.
        """
        term = (search_term or "").strip()
        if term and not self.is_search_results_page(term):
            self.search_products(term)

        grid_ok, grid_count = self.validate_grid_view()
        grid_product_ok = True
        if product_name:
            grid_product_ok, _ = self.listing.validate_application_name(product_name)

        list_ok, list_count = self.validate_list_view()
        list_product_ok = True
        if product_name:
            list_product_ok, _ = self.listing.validate_application_name(product_name)

        return {
            "on_search_page": self.is_search_results_page(term),
            "grid_ok": grid_ok,
            "grid_count": grid_count,
            "list_ok": list_ok,
            "list_count": list_count,
            "grid_product_ok": grid_product_ok,
            "list_product_ok": list_product_ok,
        }

    def validate_grid_view(self):
        try:
            self.switch_to_grid_view()
        except AssertionError:
            pass
        active = self.is_grid_view_active()
        count = self.get_product_link_count()
        if not active and count > 0:
            # Retry once — toggle can lag after filters/search
            try:
                self.switch_to_grid_view()
                active = self.is_grid_view_active()
            except AssertionError:
                pass
        return active, count

    def validate_list_view(self):
        try:
            self.switch_to_list_view()
        except AssertionError:
            pass
        active = self.is_list_view_active()
        count = self.get_product_link_count()
        if not active and count > 0:
            try:
                self.switch_to_list_view()
                active = self.is_list_view_active()
            except AssertionError:
                pass
        return active, count

    def apply_category_subcategory(self, category_subcategory=""):
        """Apply filters from category_subcategory column (simple or multi-line format)."""
        from utilities.category_parser import parse_filter_terms, parse_ticket_sections

        if not category_subcategory:
            return {}

        sections = parse_ticket_sections(category_subcategory)
        if sections:
            return self.apply_ticket_filters(category_subcategory, product_type=None)

        terms = parse_filter_terms(category_subcategory)
        results = {}
        for term in terms:
            results[term] = self.select_filter(term)

        applied = sum(1 for ok in results.values() if ok)
        self.logger.info(
            "Filters applied: %d/%d — %s",
            applied,
            len(terms),
            [k for k, v in results.items() if ok],
        )
        return results

    def apply_ticket_filters(self, category_subcategory="", product_type=None):
        """
        Client ticket order on Partner Spotlight:
        1. Edge AI Application / Edge AI System tab (if product_type given)
        2. Expand sidebar section (category) and check sub-category values
        """
        from utilities.category_parser import (
            filter_result_key,
            format_category_subcategory_report,
            parse_category_subcategory_pairs,
            parse_sidebar_filter_sections,
            parse_ticket_sections,
        )

        results = {}
        all_pairs = parse_category_subcategory_pairs(category_subcategory)
        if all_pairs:
            self.logger.info(
                "Category/Sub Category from Excel (%d):\n%s",
                len(all_pairs),
                format_category_subcategory_report(all_pairs),
            )

        if product_type:
            ok, msg = self.select_product_type(product_type)
            results[filter_result_key("Product Type", product_type.title())] = ok
            self.logger.info("Product type tab: %s — %s", product_type, msg)
            self.page.wait_for_timeout(1200)

        sections = parse_sidebar_filter_sections(category_subcategory) or parse_ticket_sections(
            category_subcategory
        )
        for sec in sections:
            section = sec["section"]
            sidebar_label = sec.get("sidebar_label") or section
            self.expand_filter_section(sidebar_label)
            self._scroll_sidebar()
            self.page.wait_for_timeout(1200)

            for value in sec["values"]:
                key = filter_result_key(section, value)
                results[key] = self.select_checkbox_filter(
                    value,
                    section_name=sidebar_label,
                    expand_section=False,
                )
                self.page.wait_for_timeout(400)

        applied = [name for name, ok in results.items() if ok]
        failed = [name for name, ok in results.items() if not ok]
        self.logger.info(
            "Category filters applied: %d/%d",
            len(applied),
            len(results),
        )
        for name in applied:
            self.logger.info("  [applied] %s", name)
        for name in failed:
            self.logger.info("  [not in sidebar] %s", name)
        return results

    def apply_filters(self, category=None, subcategory=None):
        """Legacy helper — prefer apply_category_subcategory."""
        combined = ""
        if category and subcategory:
            combined = f"{category} > {subcategory}"
        elif category:
            combined = category
        elif subcategory:
            combined = subcategory
        return self.apply_category_subcategory(combined)

    def validate_listing(self, product_name, short_description=""):
        results = {}
        ok, msg, count = self.listing.verify_listing_displayed()
        results["listing"] = (ok, msg)
        ok, msg = self.listing.validate_application_name(product_name)
        results["name"] = (ok, msg)
        ok, msg = self.listing.validate_short_description(product_name, short_description)
        results["description"] = (ok, msg)
        ok, msg, _ = self.listing.validate_partner_logo_on_listing()
        results["logo"] = (ok, msg)
        return results

    def validate_quick_view(self, product_name, expected_snippet=""):
        return self.listing.validate_quick_view(product_name, expected_snippet)

    def open_product(self, product_name):
        for selector in [
            f"a[href*='/partner-spotlight/']:visible:text-is('{product_name}')",
            f"a:has-text('Product Details') >> xpath=.. >> a:has-text('{product_name}')",
        ]:
            link = self.page.locator(selector).first
            if link.count() > 0:
                link.click()
                self.wait_for_page_load()
                self.auto_slow_scroll_if_visual()
                self.logger.info("Opened product via title: %s", product_name)
                return

        pd = self.page.locator(
            f"{PRODUCT_LINK_SELECTORS[1]} >> xpath=ancestor::*[contains(@class,'listview') or contains(@class,'gridview')][1]"
        ).filter(has=self.page.locator(f"a:has-text('{product_name}')")).locator(
            "a:has-text('Product Details')"
        ).first
        if pd.count() > 0:
            pd.click()
            self.wait_for_page_load()
            self.auto_slow_scroll_if_visual()
            return

        self.page.get_by_role("link", name=product_name).first.click()
        self.wait_for_page_load()
        self.auto_slow_scroll_if_visual()

    def open_product_details_link(self, product_name):
        card = self.listing.get_listing_card_for_product(product_name)
        if card.count():
            card.scroll_into_view_if_needed()
            self.page.wait_for_timeout(500)
            for sel in ["a:has-text('Product Details')", f"a:has-text('{product_name}')"]:
                link = card.locator(sel).first
                if link.count():
                    try:
                        link.click(timeout=5000)
                        self.wait_for_page_load()
                        self.auto_slow_scroll_if_visual()
                        return
                    except Exception:
                        link.click(force=True)
                        self.wait_for_page_load()
                        self.auto_slow_scroll_if_visual()
                        return
        self.open_product(product_name)

    def validate_partner_logo(self, partner_name=None):
        return self.logo_validator.validate(partner_name)

    def get_visible_product_names(self):
        names = []
        for selector in PRODUCT_TITLE_SELECTORS:
            loc = self.page.locator(selector)
            for i in range(loc.count()):
                text = loc.nth(i).inner_text(timeout=3000).strip()
                if text and len(text) > 2:
                    names.append(text)
        return names
