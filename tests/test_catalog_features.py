import os
import sys

import allure
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pages.edge_catalog_page import EdgeCatalogPage
from pages.partner_spotlight_page import PartnerSpotlightPage
from tests.report_helpers import record_catalog_check
from utilities.config_reader import ConfigReader
from utilities.excel_reader import ExcelReader
from utilities.logger import get_logger
from utilities.metadata_validator import MetadataValidator

logger = get_logger(__name__)


def _catalog_search_term_from_excel():
    """Use search_term from first enabled Excel row; fallback for catalog smoke only."""
    rows = ExcelReader().get_partner_products()
    if rows:
        term = (
            str(rows[0].get("search_term") or "").strip()
            or str(rows[0].get("product_name") or "").strip()
            or str(rows[0].get("partner_name") or "").strip()
        )
        if term:
            return term
    return os.getenv("CATALOG_SEARCH_TERM", "edge")


@allure.feature("Edge Catalog")
@allure.story("Catalog landing page smoke checks")
@pytest.mark.smoke
@pytest.mark.catalog
def test_catalog_page_metadata_and_breadcrumbs(page):
    catalog = EdgeCatalogPage(page)

    with allure.step("Open Edge AI Catalog"):
        catalog.open()
        catalog.validate_page_loaded()

    with allure.step("Validate catalog metadata"):
        validator = MetadataValidator(page)
        ok, message, metadata = validator.validate(
            {"title": "Edge AI Catalog"}
        )
        record_catalog_check(
            test_id="CAT-001",
            step_num=1,
            step_title="Validate catalog metadata",
            field_name="Page Title",
            expected="Edge AI Catalog",
            actual=str(metadata.get("title", message)),
            passed=ok,
            message=message,
        )
        assert ok, message
        allure.attach(str(metadata), name="metadata", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Validate catalog page URL"):
        expected_url = ConfigReader.get("edge_catalog_url")
        url_ok = expected_url in page.url
        record_catalog_check(
            test_id="CAT-001",
            step_num=2,
            step_title="Validate catalog page URL",
            field_name="Page URL",
            expected=expected_url,
            actual=page.url,
            passed=url_ok,
        )
        assert url_ok


@allure.feature("Edge Catalog")
@allure.story("Grid and list view toggle on Partner Spotlight search results")
@pytest.mark.regression
@pytest.mark.catalog
def test_catalog_view_toggle(page):
    search_term = _catalog_search_term_from_excel()
    spotlight = PartnerSpotlightPage(page)
    spotlight.open()

    with allure.step(f"Search products for '{search_term}'"):
        count = spotlight.search_products(search_term)
        logger.info("Search results count: %d for term: %s", count, search_term)
        record_catalog_check(
            test_id="CAT-002",
            step_num=1,
            step_title=f"Search products for '{search_term}'",
            field_name="Search Results",
            expected=f"> 0 results for '{search_term}'",
            actual=str(count),
            passed=count > 0,
        )
        assert count > 0, f"No products found for search term: {search_term}"
        assert spotlight.is_search_results_page(search_term), (
            f"Expected search results page with pSearch param: {page.url}"
        )

    with allure.step("Switch to grid view on search results"):
        grid_ok, grid_count = spotlight.validate_grid_view()
        logger.info("Grid view active=%s, products=%d", grid_ok, grid_count)
        record_catalog_check(
            test_id="CAT-002",
            step_num=2,
            step_title="Switch to grid view on search results",
            field_name="Grid View",
            expected="Grid active with search results",
            actual=f"active={grid_ok}, count={grid_count}",
            passed=grid_ok and grid_count > 0,
        )

    with allure.step("Switch to list view on search results"):
        list_ok, list_count = spotlight.validate_list_view()
        logger.info("List view active=%s, products=%d", list_ok, list_count)
        record_catalog_check(
            test_id="CAT-002",
            step_num=3,
            step_title="Switch to list view on search results",
            field_name="List View",
            expected="List active with search results",
            actual=f"active={list_ok}, count={list_count}",
            passed=list_ok and list_count > 0,
        )

    assert grid_ok or list_ok, "Neither grid nor list view could be validated after search"
    assert grid_count > 0 or list_count > 0, "No products on search results page"


@allure.feature("Edge Catalog")
@allure.story("Partner Spotlight in-page search")
@pytest.mark.smoke
@pytest.mark.catalog
def test_catalog_search(page):
    search_term = _catalog_search_term_from_excel()
    spotlight = PartnerSpotlightPage(page)
    spotlight.open()

    with allure.step(f"Search products for '{search_term}'"):
        count = spotlight.search_products(search_term)
        catalog_count = spotlight.listing.get_catalog_product_count()
        logger.info(
            "Search results count: %d for term: %s (catalog header: %s)",
            count,
            search_term,
            catalog_count if catalog_count is not None else "n/a",
        )
        record_catalog_check(
            test_id="CAT-003",
            step_num=1,
            step_title=f"Search products for '{search_term}'",
            field_name="Search Results",
            expected=f"> 0 results for '{search_term}'",
            actual=str(count),
            passed=count > 0,
        )
        if catalog_count is not None:
            record_catalog_check(
                test_id="CAT-003",
                step_num=1,
                step_title=f"Search products for '{search_term}'",
                field_name="Catalog Header Count",
                expected="Displayed after search",
                actual=str(catalog_count),
                passed=True,
            )

    url_ok = "partner-spotlight" in page.url
    content_ok = f"pSearch={search_term}" in page.url or search_term.lower() in page.content().lower()
    record_catalog_check(
        test_id="CAT-003",
        step_num=2,
        step_title="Verify search URL and content",
        field_name="Search URL / Content",
        expected=f"partner-spotlight with term '{search_term}'",
        actual=page.url,
        passed=url_ok and content_ok,
    )
    assert url_ok
    assert content_ok
    assert count > 0, f"No products found for search term: {search_term}"
