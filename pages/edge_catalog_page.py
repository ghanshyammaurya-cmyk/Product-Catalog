from pages.base_page import BasePage
from utilities.config_reader import ConfigReader
from utilities.constants import EXPLORE_PARTNER_SPOTLIGHT_SELECTORS


class EdgeCatalogPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.catalog_url = ConfigReader.get("edge_catalog_url")

    def open(self):
        self.navigate_to(self.catalog_url)
        self.accept_cookies_if_present()

    def click_explore_partner_spotlight(self):
        """Step 4: Click Explore Partner Spotlight on catalog Overview."""
        self.scroll_to_section("partner-spotlight")
        self.click_first_visible(EXPLORE_PARTNER_SPOTLIGHT_SELECTORS)
        self.wait_for_page_load()
        self.auto_slow_scroll_if_visual()
        self.logger.info("Clicked Explore Partner Spotlight")

    def verify_catalog_page_loaded(self):
        title = self.page.title()
        assert "Edge AI Catalog" in title or "Catalog" in title, f"Unexpected title: {title}"
        return title

    def validate_page_loaded(self):
        return self.verify_catalog_page_loaded()

    def open_partner_spotlight(self):
        """Fallback direct URL if explore link not used."""
        self.navigate_to(ConfigReader.get("partner_spotlight_url"))
