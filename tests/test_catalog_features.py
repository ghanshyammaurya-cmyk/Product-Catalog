import os
import sys

import allure
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pages.edge_catalog_page import EdgeCatalogPage
from pages.partner_spotlight_page import PartnerSpotlightPage
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
        assert ok, message
        allure.attach(str(metadata), name="metadata", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Validate catalog page URL"):
        assert ConfigReader.get("edge_catalog_url") in page.url


@allure.feature("Edge Catalog")
@allure.story("Grid and list view toggle on Partner Spotlight")
@pytest.mark.regression
@pytest.mark.catalog
def test_catalog_view_toggle(page):
    spotlight = PartnerSpotlightPage(page)
    spotlight.open()

    with allure.step("Switch to grid view"):
        grid_ok, grid_count = spotlight.validate_grid_view()
        logger.info("Grid view active=%s, products=%d", grid_ok, grid_count)

    with allure.step("Switch to list view"):
        list_ok, list_count = spotlight.validate_list_view()
        logger.info("List view active=%s, products=%d", list_ok, list_count)

    assert grid_ok or list_ok, "Neither grid nor list view could be validated"
    assert grid_count > 0 or list_count > 0, "No products found on Partner Spotlight"


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

    assert "partner-spotlight" in page.url
    assert f"pSearch={search_term}" in page.url or search_term.lower() in page.content().lower()
    assert count > 0, f"No products found for search term: {search_term}"
