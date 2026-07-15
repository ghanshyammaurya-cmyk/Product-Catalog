"""Targeted live verification for listing badge and Quick View."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

from pages.partner_spotlight_page import PartnerSpotlightPage


PRODUCT = os.environ.get("VERIFY_PRODUCT", "Ecrio Edge AI Communication Platform")
PRODUCT_TYPE = os.environ.get("VERIFY_PRODUCT_TYPE", "application")


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        spotlight = PartnerSpotlightPage(page)
        spotlight.open_for_product_type(PRODUCT_TYPE)
        count = spotlight.search_products(PRODUCT)
        badge = spotlight.listing.get_product_type_badge(PRODUCT)
        quick_ok, quick_msg = spotlight.validate_quick_view(PRODUCT)
        print(f"product={PRODUCT}")
        print(f"count={count}")
        print(f"badge={badge}")
        print(f"quick_view={quick_ok}: {quick_msg}")
        browser.close()


if __name__ == "__main__":
    main()
