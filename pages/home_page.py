from pages.base_page import BasePage
from utilities.config_reader import ConfigReader
from utilities.constants import MAIN_MENU_SELECTORS


class HomePage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.base_url = ConfigReader.get("base_url")

    def open(self):
        self.navigate_to(self.base_url)
        self.accept_cookies_if_present()

    def open_engagement_menu(self):
        """Step 2: Hover Engagement top-level menu."""
        for selector in MAIN_MENU_SELECTORS["engagement"]:
            loc = self.page.locator(selector).first
            try:
                if loc.is_visible(timeout=3000):
                    loc.hover()
                    self.page.wait_for_timeout(800)
                    self.logger.info("Engagement menu opened via: %s", selector)
                    return True
            except Exception:
                continue
        self.logger.warning("Engagement menu not found")
        return False

    def navigate_to_edge_catalog_from_menu(self):
        """Step 3: Solution Hub -> Edge AI Catalog via menu clicks."""
        for selector in MAIN_MENU_SELECTORS["solution_hub"]:
            loc = self.page.locator(selector).first
            try:
                if loc.is_visible(timeout=3000):
                    loc.hover()
                    self.page.wait_for_timeout(800)
                    break
            except Exception:
                continue

        for selector in MAIN_MENU_SELECTORS["edge_ai_catalog"]:
            loc = self.page.locator(selector).first
            try:
                if loc.is_visible(timeout=3000):
                    loc.click()
                    self.wait_for_page_load()
                    self.auto_slow_scroll_if_visual()
                    self.logger.info("Navigated to Edge AI Catalog via menu")
                    return True
            except Exception:
                continue

        self.logger.warning("Menu navigation to catalog failed")
        return False

    def navigate_to_edge_catalog_via_menu(self):
        """Steps 1-3 combined (legacy entry point)."""
        self.open()
        if self.navigate_to_edge_catalog_from_menu():
            return True
        self.logger.warning("Menu navigation failed — using direct catalog URL")
        self.navigate_to(ConfigReader.get("edge_catalog_url"))
        return False
