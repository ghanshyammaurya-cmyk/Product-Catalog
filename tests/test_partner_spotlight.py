"""
Partner Spotlight — Excel-driven multi-product tests (same file).

Each row with enabled=TRUE (or 1) in testdata/partner_products.xlsx runs the flow.
Rows with enabled=FALSE (or 0) are skipped automatically.
"""

import os
import sys

import allure
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tests.partner_spotlight_flow import PartnerSpotlight26StepFlow
from utilities.test_data_provider import load_partner_product_data, partner_product_ids


def pytest_generate_tests(metafunc):
    """Load Excel rows fresh on each test collection (respects enabled column)."""
    if "product_data" not in metafunc.fixturenames:
        return
    if "test_partner_spotlight" not in metafunc.module.__name__:
        return

    rows = load_partner_product_data()
    if not rows:
        metafunc.parametrize(
            "product_data",
            [pytest.param({}, marks=pytest.mark.skip(reason="No enabled rows in Excel"))],
            ids=["no-enabled-data"],
        )
        return

    metafunc.parametrize(
        "product_data",
        rows,
        ids=[partner_product_ids(row) for row in rows],
    )


@allure.feature("Partner Spotlight")
@allure.story("Full 26-step Edge AI Catalog validation")
@pytest.mark.regression
@pytest.mark.partner
def test_partner_spotlight_26_step_flow(page, product_data):
    """Run all 26 manual test steps for each enabled Excel product row."""
    PartnerSpotlight26StepFlow(page, product_data, capture_screenshots=True).run()


@pytest.mark.smoke
def test_partner_spotlight_listing_smoke(page, product_data):
    """Lightweight smoke: search + listing checks only (steps 11, 8, 13)."""
    from pages.partner_spotlight_page import PartnerSpotlightPage
    from tests.helpers import get_str
    from utilities.step_reporter import StepReporter

    test_id = get_str(product_data, "test_id", "unknown")
    product_name = get_str(product_data, "product_name")
    search_term = get_str(product_data, "search_term") or product_name
    partner_name = get_str(product_data, "partner_name")
    reporter = StepReporter(page, test_id)

    spotlight = PartnerSpotlightPage(page)
    spotlight.open()

    reporter.run(11, "Search product and verify results", lambda: None)
    count = spotlight.search_products(search_term)
    reporter.record_check(
        step_num=11,
        step_title="Search product and verify results",
        field_name="Search Results",
        expected=f"> 0 for '{search_term}'",
        actual=str(count),
        passed=count > 0,
    )
    assert count > 0, f"No search results for: {search_term}"

    reporter.run(8, "Validate application name on listing", lambda: None)
    ok, msg = spotlight.listing.validate_application_name(product_name)
    reporter.record_check(
        step_num=8,
        step_title="Validate application name on listing",
        field_name="Application Name",
        expected=product_name,
        actual=msg,
        passed=ok,
        message=msg,
    )
    assert ok, msg

    reporter.run(13, "Verify Partner Logo on listing page", lambda: None)
    ok, msg, _ = spotlight.listing.validate_partner_logo_on_listing(partner_name)
    reporter.record_check(
        step_num=13,
        step_title="Verify Partner Logo on listing page",
        field_name="Partner Logo",
        expected=partner_name,
        actual=msg,
        passed=ok,
        message=msg,
    )
    assert ok, msg
