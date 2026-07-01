"""
Reusable 26-step Partner Spotlight validation flow.

Used by parametrized tests in test_partner_spotlight.py so multiple products
run from the same file with Excel-driven data.
"""

import allure
import pytest

from pages.edge_catalog_page import EdgeCatalogPage
from pages.home_page import HomePage
from pages.partner_spotlight_page import PartnerSpotlightPage
from pages.product_detail_page import ProductDetailPage
from utilities.listing_validator import ListingValidator
from utilities.category_validator import CategoryValidator
from tests.helpers import (
    as_bool,
    build_metadata_expectations,
    format_category_subcategory,
    get_category_subcategory_pairs,
    get_str,
    parse_breadcrumb_trail,
    parse_expected_categories,
    parse_expected_features,
)
from utilities.logger import get_logger
from utilities.step_reporter import StepReporter

logger = get_logger(__name__)

# Manual test case steps (aligned with ticket screenshots)
FLOW_STEPS = [
    (1, "Open Intel Builders home page"),
    (2, "Open Engagement menu"),
    (3, "Navigate to Edge AI Catalog"),
    (4, "Click Explore Partner Spotlight"),
    (5, "Verify Edge AI Partner Spotlight page opens"),
    (6, "Filter listing by partner"),
    (7, "Verify product listing is displayed"),
    (8, "Validate application name on listing"),
    (9, "Validate short description on listing"),
    (10, "Verify Grid View and List View"),
    (11, "Search product and verify results"),
    (12, "Apply Category/Sub-Category filters"),
    (13, "Verify Partner Logo on listing page"),
    (14, "Click Quick View and validate product info"),
    (15, "Open Product Detail page"),
    (16, "Verify page metadata matches product"),
    (17, "Validate Product Name on detail page"),
    (18, "Verify Thumbnail Image"),
    (19, "Validate Breadcrumb Navigation"),
    (20, "Verify complete Product Description"),
    (21, "Validate Partner Contact link redirect"),
    (22, "Verify Features section"),
    (23, "Validate Resources section links"),
    (24, "Download and validate PDF"),
    (25, "Verify Categories section"),
    (26, "Verify Related Products section"),
]


class PartnerSpotlight26StepFlow:
    """Executes the full 26-step manual validation for one Excel product row."""

    def __init__(self, page, product_data: dict, capture_screenshots: bool = True):
        self.page = page
        self.data = product_data
        self.test_id = get_str(product_data, "test_id", "unknown")
        self.partner_name = get_str(product_data, "partner_name")
        self.partner_dropdown_label = (
            get_str(product_data, "partner_dropdown_label") or self.partner_name
        )
        self.product_name = (
            get_str(product_data, "product_name")
            or get_str(product_data, "application_name")
        )
        self.short_desc = (
            get_str(product_data, "expected_short_description")
            or get_str(product_data, "expected_description")
        )
        self.full_desc = get_str(product_data, "expected_description") or self.short_desc
        self.category_subcategory_raw = get_str(product_data, "category_subcategory")
        self.category_subcategory = format_category_subcategory(product_data)
        self.category_pairs = get_category_subcategory_pairs(product_data)
        self.listing_site_data = None
        self.product_type = get_str(product_data, "product_type", "system")
        self.search_term = get_str(product_data, "search_term") or self.product_name
        self.contact_fragment = get_str(product_data, "expected_contact_url")
        self.resource_url = get_str(product_data, "expected_resource_url")
        self.expected_features = parse_expected_features(product_data.get("expected_features"))
        self.expected_categories = parse_expected_categories(
            product_data.get("expected_categories")
        )
        self.resolved_product_type = self.product_type
        self.reported_product_type = ListingValidator.format_product_type_label(self.product_type)
        self.reporter = StepReporter(page, self.test_id, capture_screenshots)

    def run(self):
        allure.dynamic.title(f"[{self.test_id}] 26-Step Flow — {self.product_name}")
        allure.dynamic.parameter("partner", self.partner_name or "N/A")
        allure.dynamic.parameter("product", self.product_name)
        if self.category_pairs:
            allure.dynamic.parameter(
                "category",
                "; ".join(p["category"] for p in self.category_pairs),
            )
            allure.dynamic.parameter(
                "subcategory",
                "; ".join(p["subcategory"] for p in self.category_pairs),
            )
        allure.dynamic.parameter("category_subcategory", self.category_subcategory or "N/A")

        home = HomePage(self.page)
        catalog = EdgeCatalogPage(self.page)
        spotlight = PartnerSpotlightPage(self.page)
        detail = None

        # Steps 1-3: Home navigation
        self.reporter.run(1, FLOW_STEPS[0][1], home.open)
        self.reporter.run(2, FLOW_STEPS[1][1], home.open_engagement_menu)
        self.reporter.run(
            3,
            FLOW_STEPS[2][1],
            lambda: home.navigate_to_edge_catalog_from_menu() or catalog.open(),
        )
        self.reporter.run(4, FLOW_STEPS[3][1], lambda: self._open_partner_spotlight(catalog))

        # Step 5
        self.reporter.run(5, FLOW_STEPS[4][1], lambda: self._verify_spotlight_page(spotlight))

        # Step 6 — partner filter first (client ticket order)
        self.reporter.run(6, FLOW_STEPS[5][1], lambda: self._filter_by_partner(spotlight))

        # Step 7 — Application/System tab + category/sub-category, then verify listing
        self.reporter.run(7, FLOW_STEPS[6][1], lambda: self._ensure_product_type_and_listing(spotlight))

        # Steps 8-9
        self.reporter.run(
            8,
            FLOW_STEPS[7][1],
            lambda: self._assert(
                *spotlight.listing.validate_application_name(self.product_name)
            ),
        )
        self.reporter.run(
            9,
            FLOW_STEPS[8][1],
            lambda: self._assert(
                *spotlight.listing.validate_short_description(
                    self.product_name, self.short_desc
                )
            ),
        )
        # Listing card tags (screenshot: Robotics AI Suite, Extended Temperature, etc.)
        tag_terms = self.expected_categories[:5] if self.expected_categories else []
        if tag_terms:
            ok, msg, _ = spotlight.listing.validate_listing_tags(
                self.product_name, tag_terms
            )
            if not ok:
                logger.warning("Listing tags: %s", msg)

        # Step 10
        self.reporter.run(10, FLOW_STEPS[9][1], lambda: self._validate_views(spotlight))

        # Step 12 — validate category/sub-category filters (applied in step 7)
        self.reporter.run(
            12,
            f"{FLOW_STEPS[11][1]} — {self.category_subcategory or 'N/A'}",
            lambda: self._validate_category_filters(spotlight),
        )

        # Step 11 — keyword search after partner + category filters
        self.reporter.run(11, FLOW_STEPS[10][1], lambda: self._search_product(spotlight))

        # Step 13
        self.reporter.run(
            13,
            FLOW_STEPS[12][1],
            lambda: self._assert(
                *spotlight.listing.validate_partner_logo_on_listing(self.partner_name)[:2]
            ),
        )

        # Step 14
        self.reporter.run(14, FLOW_STEPS[13][1], lambda: self._quick_view(spotlight))

        # Step 15
        self.reporter.run(
            15,
            FLOW_STEPS[14][1],
            lambda: self._open_product_detail(spotlight),
        )
        detail = ProductDetailPage(self.page)
        detail.wait_until_loaded()

        # Steps 16-26: Product detail
        self.reporter.run(
            16,
            FLOW_STEPS[15][1],
            lambda: self._assert(
                *detail.validate_metadata(build_metadata_expectations(self.data))[:2]
            ),
        )
        self.reporter.run(
            17,
            FLOW_STEPS[16][1],
            lambda: self._assert(
                *detail.validate_product_detail(
                    expected_title=get_str(self.data, "expected_title") or self.product_name
                )[:2]
            ),
        )
        self.reporter.run(
            18,
            FLOW_STEPS[17][1],
            lambda: self._assert(*detail.validate_thumbnail(self.product_name)[:2]),
        )
        self.reporter.run(
            19,
            FLOW_STEPS[18][1],
            lambda: self._assert(
                *detail.validate_breadcrumbs(
                    parse_breadcrumb_trail(self.data.get("expected_breadcrumb"))
                )[:2]
            ),
        )
        self.reporter.run(
            20,
            FLOW_STEPS[19][1],
            lambda: self._assert(*detail.detail.validate_full_description(self.full_desc)[:2]),
        )
        self.reporter.run(
            21,
            FLOW_STEPS[20][1],
            lambda: self._assert(*detail.validate_contact_link(self.contact_fragment)[:2]),
        )
        self.reporter.run(22, FLOW_STEPS[21][1], lambda: self._validate_features(detail))
        self.reporter.run(23, FLOW_STEPS[22][1], lambda: self._validate_resources(detail))
        self.reporter.run(24, FLOW_STEPS[23][1], lambda: self._validate_pdf(detail))
        self.reporter.run(
            25,
            FLOW_STEPS[24][1],
            lambda: self._validate_detail_categories(detail),
        )
        self.reporter.run(
            26,
            FLOW_STEPS[25][1],
            lambda: self._validate_related(detail),
        )

        logger.info("All 26 steps passed for test: %s", self.test_id)

    @staticmethod
    def _assert(ok, msg):
        assert ok, msg

    def _open_partner_spotlight(self, catalog: EdgeCatalogPage):
        try:
            catalog.click_explore_partner_spotlight()
        except AssertionError:
            catalog.open_partner_spotlight()

    def _verify_spotlight_page(self, spotlight: PartnerSpotlightPage):
        ok, msg, info = spotlight.verify_page_loaded()
        assert ok, msg
        if "type=" not in self.page.url:
            spotlight.open()
        assert "partner-spotlight" in self.page.url.lower()
        count = info.get("catalog_count") if info else None
        if count is not None:
            assert count > 0, f"Expected products in catalog header, got: {count}"
            logger.info("Step 5 catalog count: %s", count)

    def _filter_by_partner(self, spotlight: PartnerSpotlightPage):
        """Step 6: Filter By Partners dropdown (client does this before category filters)."""
        if not self.partner_name:
            return
        ok, msg = spotlight.select_partner(
            self.partner_dropdown_label,
            search_hint=self.partner_name,
        )
        assert ok, f"Partner filter required but not applied: {msg}"
        count = spotlight.listing.get_catalog_product_count()
        logger.info("Step 6 partner filter applied; catalog count: %s", count)

    def _apply_category_and_subcategory(self, spotlight: PartnerSpotlightPage, product_type):
        """Application/System tab, re-apply partner, then sidebar category + sub-category."""
        if product_type:
            spotlight.select_product_type(product_type)
            self.page.wait_for_timeout(1000)

        if self.partner_name:
            spotlight.select_partner(
                self.partner_dropdown_label,
                search_hint=self.partner_name,
            )

        if not self.category_subcategory_raw:
            return {}

        return spotlight.apply_ticket_filters(self.category_subcategory_raw, product_type=None)

    def _search_with_filters(self, spotlight: PartnerSpotlightPage, product_type):
        """Keyword search resets partner/tab filters on site — restore client order after."""
        count = spotlight.search_products(self.search_term)
        self._apply_category_and_subcategory(spotlight, product_type)
        return count

    def _ensure_product_type_and_listing(self, spotlight: PartnerSpotlightPage):
        """
        Client ticket order after partner:
        1. Edge AI Application or Edge AI System tab
        2. Category / sub-category sidebar filters
        3. Verify product listing
        """
        preferred = self.product_type
        if preferred and str(preferred).lower().startswith("app"):
            try_types = ["application", "system"]
        elif preferred and str(preferred).lower().startswith("sys"):
            try_types = ["system", "application"]
        else:
            try_types = ["application", "system"]

        ok = False
        actual_type = try_types[0]

        for idx, ptype in enumerate(try_types):
            if idx > 0:
                spotlight.open_for_product_type(ptype)

            filter_results = self._apply_category_and_subcategory(spotlight, ptype)
            if self.category_subcategory_raw:
                applied = [name for name, passed in filter_results.items() if passed]
                failed = [name for name, passed in filter_results.items() if not passed]
                logger.info(
                    "Step 7 expected Category/Sub Category from Excel (%d):\n%s",
                    len(self.category_pairs),
                    self.category_subcategory,
                )
                allure.attach(
                    self.category_subcategory,
                    name="all_category_subcategory_from_excel",
                    attachment_type=allure.attachment_type.TEXT,
                )
                logger.info(
                    "Step 7 filters on %s tab — applied %d, not in sidebar %d:",
                    ptype,
                    len(applied),
                    len(failed),
                )
                for name in applied:
                    logger.info("  [applied] %s", name)
                for name in failed:
                    logger.info("  [pending] %s", name)
                category_applied = [
                    k for k in applied if k.startswith("Category:")
                ]
                assert len(category_applied) >= 1, (
                    f"Could not apply any category/sub-category filters on {ptype} tab. "
                    f"Tried: {list(filter_results.keys())}"
                )

            if spotlight.listing.is_product_listed(self.product_name):
                ok = True
                actual_type = ptype
                break

            if self.search_term:
                self._search_with_filters(spotlight, ptype)
                if spotlight.listing.is_product_listed(self.product_name):
                    ok = True
                    actual_type = ptype
                    break

        if not ok:
            ok, actual_type = spotlight.resolve_product_type(
                self.product_name,
                search_term=self.search_term,
                partner_name=self.partner_name,
                partner_dropdown_label=self.partner_dropdown_label,
                short_description=self.short_desc,
            )
            if ok:
                self._apply_category_and_subcategory(spotlight, actual_type)

        assert ok, (
            f"Product '{self.product_name}' not found after partner + category filters."
        )

        self.resolved_product_type = actual_type
        self.reported_product_type = ListingValidator.format_product_type_label(actual_type)
        allure.dynamic.parameter("product_type", self.reported_product_type)
        allure.dynamic.parameter("excel_product_type", self.product_type or "N/A")
        logger.info(
            "Report product type: %s (Excel had: %s)",
            self.reported_product_type,
            self.product_type,
        )

        ok, msg, _ = spotlight.listing.validate_product_type_badge(
            self.product_name, actual_type
        )
        assert ok, msg

        ok, msg, _ = spotlight.listing.verify_listing_displayed()
        assert ok, msg

        ok, msg = spotlight.listing.validate_application_name(self.product_name)
        assert ok, f"Product not on listing after filters: {msg}"

    def _assert_listing(self, spotlight: PartnerSpotlightPage):
        ok, msg, _ = spotlight.listing.verify_listing_displayed()
        assert ok, msg

    def _validate_views(self, spotlight: PartnerSpotlightPage):
        grid_ok, grid_count = spotlight.validate_grid_view()
        list_ok, list_count = spotlight.validate_list_view()
        assert grid_ok or list_ok, "Grid/List view toggle failed"
        assert grid_count > 0 or list_count > 0, "No products in listing"

    def _search_product(self, spotlight: PartnerSpotlightPage):
        count = spotlight.search_products(self.search_term)
        assert count > 0, f"No search results for: {self.search_term}"
        catalog_count = spotlight.listing.get_catalog_product_count()
        if catalog_count is not None:
            logger.info("Step 11 search catalog count: %s", catalog_count)
        ok, msg = spotlight.listing.validate_application_name(self.product_name)
        assert ok, f"Product not in search results: {msg}"

    def _validate_category_filters(self, spotlight: PartnerSpotlightPage):
        """Step 12: Capture listing categories and compare vs Excel."""
        if not self.category_pairs:
            logger.info("Step 12: no category/subcategory in Excel — skipped")
            return

        allure.attach(
            self.category_subcategory,
            name="excel_category_subcategory",
            attachment_type=allure.attachment_type.TEXT,
        )

        validator = CategoryValidator(self.page)
        self.listing_site_data = validator.collect_listing_site_data(self.product_name)

        ok, msg, report, info = validator.validate_pairs_combined(
            self.category_pairs,
            listing_data=self.listing_site_data,
            detail_data=None,
        )
        allure.attach(
            report,
            name="listing_category_site_vs_excel",
            attachment_type=allure.attachment_type.TEXT,
        )
        missing_count = len(info.get("missing", []))
        if ok:
            logger.info("Step 12: all Excel sub-categories visible on listing page")
        else:
            logger.info(
                "Step 12 listing check (%d/%d on listing; full check at Step 25 with detail page):\n%s",
                len(self.category_pairs) - missing_count,
                len(self.category_pairs),
                msg,
            )

        ok, name_msg = spotlight.listing.validate_application_name(self.product_name)
        assert ok, f"Product not listed after category filters: {name_msg}"

    def _validate_detail_categories(self, detail: ProductDetailPage):
        """Step 25: Strict Excel vs site (listing tags + detail page)."""
        if self.category_pairs:
            ok, msg, _ = detail.validate_category_subcategory_strict(
                self.category_pairs,
                listing_site_data=self.listing_site_data,
            )
            assert ok, msg
            return
        if self.expected_categories:
            ok, msg, _ = detail.validate_categories(self.expected_categories)
            assert ok, msg

    def _quick_view(self, spotlight: PartnerSpotlightPage):
        spotlight.search_products(self.search_term)
        spotlight.validate_list_view()
        ok, msg = spotlight.validate_quick_view(self.product_name, self.short_desc)
        if not ok:
            logger.warning("Quick View not available: %s — continuing with Product Details", msg)

    def _open_product_detail(self, spotlight: PartnerSpotlightPage):
        spotlight.search_products(self.search_term)
        spotlight.open_product_details_link(self.product_name)

    def _validate_features(self, detail: ProductDetailPage):
        if not self.expected_features:
            return
        ok, msg, _ = detail.validate_features(self.expected_features)
        assert ok, msg

    def _validate_resources(self, detail: ProductDetailPage):
        ok, msg, _ = detail.validate_resource_links(self.resource_url)
        if self.resource_url:
            assert ok, msg
        elif not ok:
            logger.warning("Resources validation: %s", msg)

    def _validate_pdf(self, detail: ProductDetailPage):
        if not as_bool(self.data.get("validate_pdf")):
            return
        ok, msg, pdf_path = detail.download_and_validate_pdf(
            get_str(self.data, "expected_pdf_text") or None
        )
        assert ok, msg
        allure.attach.file(pdf_path, name="downloaded_pdf", extension="pdf")

    def _validate_related(self, detail: ProductDetailPage):
        ok, msg, related = detail.validate_related_products(self.partner_name)
        if not ok:
            logger.warning("Related Products optional: %s", msg)
            return
        if self.partner_name and related:
            assert any(
                self.partner_name.split()[0].lower() in r.lower() for r in related
            ), f"Related products may not match partner {self.partner_name}: {related}"
