from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import re

from utilities.breadcrumb_validator import BreadcrumbValidator
from utilities.config_reader import ConfigReader
from utilities.constants import (
    CATALOG_SEARCH_SELECTORS,
    COOKIE_ACCEPT_SELECTORS,
    GRID_VIEW_SELECTORS,
    LIST_VIEW_SELECTORS,
)
from utilities.logger import get_logger
from utilities.screenshot_util import ScreenshotUtil
from utilities.visual_mode import (
    get_scroll_delay_ms,
    get_scroll_step_pixels,
    is_enabled as is_visual_mode,
)


class BasePage:
    """Reusable base page with common Playwright interactions."""

    def __init__(self, page: Page):
        self.page = page
        self.timeout = ConfigReader.get("timeout", 30000)
        self.navigation_timeout = ConfigReader.get("navigation_timeout", 60000)
        self.logger = get_logger(self.__class__.__name__)
        self.screenshot_util = ScreenshotUtil(page)

    def navigate_to(self, url, wait_until="domcontentloaded"):
        self.logger.info("Navigating to: %s", url)
        self.page.goto(url, wait_until=wait_until, timeout=self.navigation_timeout)
        self.wait_for_page_load()
        self.auto_slow_scroll_if_visual()

    def auto_slow_scroll_if_visual(self):
        import os

        if not is_visual_mode():
            return
        if os.environ.get("AUTO_SLOW_SCROLL", "true").lower() == "false":
            return
        if ConfigReader.get("auto_slow_scroll", True):
            self.slow_scroll_top_to_bottom()

    def wait_for_page_load(self, state="load"):
        try:
            self.page.wait_for_load_state(state, timeout=self.navigation_timeout)
        except PlaywrightTimeoutError:
            self.logger.warning("Load state '%s' timed out — continuing", state)

    def accept_cookies_if_present(self):
        for selector in COOKIE_ACCEPT_SELECTORS:
            button = self.page.locator(selector).first
            try:
                if button.is_visible(timeout=3000):
                    button.click()
                    self.page.wait_for_timeout(500)
                    self.logger.info("Accepted cookies via: %s", selector)
                    return True
            except PlaywrightTimeoutError:
                continue
        return False

    def click_first_visible(self, selectors, timeout=None):
        timeout = timeout or self.timeout
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if locator.is_visible(timeout=3000):
                    locator.click(timeout=timeout)
                    self.logger.info("Clicked: %s", selector)
                    return True
            except PlaywrightTimeoutError:
                continue
        raise AssertionError(f"No visible element found for selectors: {selectors}")

    def click_by_role(self, role, name, exact=False):
        self.page.get_by_role(role, name=name, exact=exact).first.click()
        self.logger.info("Clicked %s: %s", role, name)

    def click_by_text(self, text, exact=False):
        self.page.get_by_text(text, exact=exact).first.click()
        self.logger.info("Clicked text: %s", text)

    def fill_first_visible(self, selectors, value):
        for selector in selectors:
            field = self.page.locator(selector).first
            try:
                if field.is_visible(timeout=3000):
                    field.fill(value)
                    self.logger.info("Filled '%s' into: %s", value, selector)
                    return field
            except PlaywrightTimeoutError:
                continue
        raise AssertionError(f"No visible input found for selectors: {selectors}")

    def catalog_search(self, term, submit=True):
        """In-page product search on Partner Spotlight (#pSearch)."""
        field = self.fill_first_visible(CATALOG_SEARCH_SELECTORS, term)
        if submit:
            field.press("Enter")
        self.page.wait_for_timeout(2000)
        self.wait_for_page_load()
        self.auto_slow_scroll_if_visual()
        self.logger.info("Catalog search for: %s", term)
        return field

    def clear_catalog_search(self):
        for selector in CATALOG_SEARCH_SELECTORS:
            field = self.page.locator(selector).first
            if field.is_visible(timeout=2000):
                field.fill("")
                field.press("Enter")
                self.page.wait_for_timeout(1500)
                return

    def switch_to_grid_view(self):
        self.click_first_visible(GRID_VIEW_SELECTORS)
        self.page.wait_for_timeout(1000)
        self.logger.info("Switched to grid view")

    def switch_to_list_view(self):
        self.click_first_visible(LIST_VIEW_SELECTORS)
        self.page.wait_for_timeout(1000)
        self.logger.info("Switched to list view")

    def _view_button_active(self, selectors):
        for selector in selectors:
            btn = self.page.locator(selector).first
            if btn.is_visible(timeout=2000):
                class_name = btn.get_attribute("class") or ""
                if "active" in class_name.lower():
                    return True
        return False

    def is_grid_view_active(self):
        if self._view_button_active(GRID_VIEW_SELECTORS):
            return True
        return self.element_count(".gridview") > 0

    def is_list_view_active(self):
        if self._view_button_active(LIST_VIEW_SELECTORS):
            return True
        return self.element_count(".listview") > 2

    def _sidebar_scope(self):
        sidebar = self.page.locator("[class*='sidebar' i], aside, [class*='filter' i]").first
        return sidebar if sidebar.count() else self.page

    def _scroll_sidebar(self):
        """Scroll filter sidebar so lazy-loaded sub-category checkboxes appear."""
        scope = self._sidebar_scope()
        try:
            scope.evaluate(
                """el => {
                    const node = el.scrollHeight > el.clientHeight ? el : document.scrollingElement;
                    node.scrollTop = node.scrollHeight;
                }"""
            )
            self.page.wait_for_timeout(700)
            scope.evaluate(
                """el => {
                    const node = el.scrollHeight > el.clientHeight ? el : document.scrollingElement;
                    node.scrollTop = 0;
                }"""
            )
            self.page.wait_for_timeout(500)
        except Exception:
            pass

    def expand_filter_section(self, section_name):
        """Expand a sidebar filter group (e.g. Device Type, Vertical)."""
        if not section_name or not str(section_name).strip():
            return False

        from utilities.category_parser import sidebar_section_label

        names = [str(section_name).strip(), sidebar_section_label(section_name)]
        seen = set()
        scope = self._sidebar_scope()

        for name in names:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            header_selectors = [
                f"a:has-text('{name}')",
                f"label:has-text('{name}')",
                f"button:has-text('{name}')",
                f"div:has-text('{name}')",
                f"span:has-text('{name}')",
            ]

            for selector in header_selectors:
                header = scope.locator(selector).first
                try:
                    if header.is_visible(timeout=2000):
                        header.scroll_into_view_if_needed()
                        header.click(timeout=5000)
                        self.page.wait_for_timeout(1000)
                        self._scroll_sidebar()
                        self.logger.info("Expanded filter section: %s", name)
                        return True
                except Exception:
                    continue

            if self.select_filter(name):
                self._scroll_sidebar()
                return True

        return False

    def _try_select_checkbox(self, value, section_name=None):
        """Try once to check a sidebar value (exact or partial label match)."""
        name = str(value).strip()
        scope = self._sidebar_scope()
        needles = [name]
        if len(name) > 24:
            needles.append(name[:24])

        for needle in needles:
            try:
                checkbox = self.page.get_by_role(
                    "checkbox", name=re.compile(re.escape(needle), re.I)
                )
                if checkbox.count():
                    box = checkbox.first
                    box.scroll_into_view_if_needed()
                    if not box.is_checked():
                        box.check(timeout=5000)
                    self.page.wait_for_timeout(800)
                    return True
            except Exception:
                pass

            label = scope.locator("label").filter(
                has_text=re.compile(re.escape(needle), re.I)
            ).first
            try:
                if label.is_visible(timeout=2000):
                    label.scroll_into_view_if_needed()
                    label.click(timeout=5000)
                    self.page.wait_for_timeout(800)
                    return True
            except Exception:
                continue

        return False

    def select_checkbox_filter(
        self, value, section_name=None, max_attempts=2, expand_section=True
    ):
        """Check a sidebar checkbox; retry with scroll for lazy-loaded options."""
        if not value or not str(value).strip():
            return False

        name = str(value).strip()
        for attempt in range(max_attempts):
            if section_name and (expand_section or attempt > 0):
                self.expand_filter_section(section_name)
                self.page.wait_for_timeout(700 + attempt * 300)

            if self._try_select_checkbox(name, section_name):
                self.logger.info("Selected checkbox filter: %s", name)
                return True

            if attempt < max_attempts - 1:
                self._scroll_sidebar()
                self.page.wait_for_timeout(600)

        if self.select_filter(name):
            self.logger.info("Selected filter (fallback): %s", name)
            return True

        self.logger.warning("Sub-category not found in sidebar: %s", name)
        return False

    def select_filter(self, filter_name):
        """Select a sidebar filter (section header or filter value). Returns True if clicked."""
        if not filter_name or not str(filter_name).strip():
            return False

        name = str(filter_name).strip()
        scope = self._sidebar_scope()
        scopes = [scope]

        selectors = "a, label, span, li, div, button, input[type='checkbox'] + label"

        for scope in scopes:
            loc = scope.locator(selectors).filter(has_text=name).first
            try:
                if loc.is_visible(timeout=2000):
                    loc.scroll_into_view_if_needed()
                    loc.click(timeout=5000)
                    self.page.wait_for_timeout(1000)
                    self.logger.info("Selected filter: %s", name)
                    return True
            except Exception:
                pass

            # Partial match (e.g. 'Edge Feature' -> 'Edge Features')
            for element in scope.locator(selectors).all()[:80]:
                try:
                    text = element.inner_text(timeout=500).strip()
                    if not text or len(text) > 80:
                        continue
                    if name.lower() in text.lower() or text.lower() in name.lower():
                        if element.is_visible(timeout=1000):
                            element.scroll_into_view_if_needed()
                            element.click(timeout=5000)
                            self.page.wait_for_timeout(1000)
                            self.logger.info("Selected filter (partial match): %s -> %s", name, text)
                            return True
                except Exception:
                    continue

        self.logger.warning("Filter not found (skipped): %s", name)
        return False

    def select_category(self, category_name):
        return self.select_filter(category_name)

    def select_subcategory(self, subcategory_name):
        return self.select_filter(subcategory_name)

    def get_breadcrumb_texts(self):
        return BreadcrumbValidator(self.page).get_breadcrumbs()

    def get_page_title(self):
        return self.page.locator("h1").first.inner_text(timeout=self.timeout)

    def get_current_url(self):
        return self.page.url

    def take_screenshot(self, name):
        return self.screenshot_util.capture(name)

    def wait_for_selector(self, selector, state="visible"):
        self.page.wait_for_selector(selector, state=state, timeout=self.timeout)

    def element_count(self, selector):
        return self.page.locator(selector).count()

    def scroll_to_section(self, section_id):
        self.page.locator(f"#{section_id}").scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)

    def scroll_to_bottom(self):
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(500)

    def slow_scroll_top_to_bottom(self, step_px=None, delay_ms=None):
        """Scroll page slowly from top to bottom (visible demo mode)."""
        step = step_px or get_scroll_step_pixels()
        delay = delay_ms or get_scroll_delay_ms()

        self.page.evaluate("window.scrollTo({ top: 0, behavior: 'instant' })")
        self.page.wait_for_timeout(delay)

        scroll_height = self.page.evaluate(
            "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        )
        viewport_height = self.page.evaluate("window.innerHeight")
        position = 0

        self.logger.info(
            "Slow scroll started: height=%d, step=%d, delay=%dms",
            scroll_height,
            step,
            delay,
        )

        while position < scroll_height - viewport_height:
            position = min(position + step, scroll_height)
            self.page.evaluate(f"window.scrollTo({{ top: {position}, behavior: 'instant' }})")
            self.page.wait_for_timeout(delay)

        self.page.evaluate(
            "window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' })"
        )
        self.page.wait_for_timeout(delay)
        self.logger.info("Slow scroll completed")
