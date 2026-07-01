import re

from playwright.sync_api import Page

from utilities.constants import BREADCRUMB_SELECTORS
from utilities.logger import get_logger

logger = get_logger(__name__)


class BreadcrumbValidator:
    """Validates breadcrumb navigation trails on builders.intel.com."""

    def __init__(self, page: Page):
        self.page = page

    def get_breadcrumbs(self):
        for selector in BREADCRUMB_SELECTORS:
            locator = self.page.locator(selector).first
            if locator.count() == 0:
                continue
            raw = locator.inner_text(timeout=5000).strip()
            if not raw:
                continue

            if "/" in raw:
                crumbs = [part.strip() for part in raw.split("/") if part.strip()]
            else:
                items = self.page.locator(selector)
                crumbs = [
                    items.nth(i).inner_text(timeout=3000).strip()
                    for i in range(items.count())
                    if items.nth(i).inner_text(timeout=3000).strip()
                ]

            if crumbs:
                logger.debug("Breadcrumbs via '%s': %s", selector, crumbs)
                return crumbs

        return []

    def validate(self, expected_trail=None):
        crumbs = self.get_breadcrumbs()
        if not crumbs:
            return False, "No breadcrumbs found on page", crumbs

        if not expected_trail:
            return True, f"Breadcrumbs present: {' > '.join(crumbs)}", crumbs

        expected = [item.strip() for item in expected_trail if item.strip()]
        missing = []
        for item in expected:
            if not any(item.lower() in crumb.lower() for crumb in crumbs):
                missing.append(item)

        if missing:
            return (
                False,
                f"Missing breadcrumb items: {missing}. Found: {crumbs}",
                crumbs,
            )

        logger.info("Breadcrumb validation passed: %s", " > ".join(crumbs))
        return True, "Breadcrumb validation passed", crumbs
