from playwright.sync_api import Page

from utilities.constants import METADATA_SELECTORS
from utilities.logger import get_logger
from utilities.text_parser import texts_match

logger = get_logger(__name__)


class MetadataValidator:
    """Validates page metadata (title, description, OG tags, canonical)."""

    def __init__(self, page: Page):
        self.page = page

    def get_metadata(self):
        metadata = {}
        metadata["title"] = self.page.title()

        for key, selector in METADATA_SELECTORS.items():
            if key == "title":
                continue
            element = self.page.locator(selector).first
            if element.count() == 0:
                metadata[key] = ""
                continue
            if key == "canonical":
                metadata[key] = element.get_attribute("href") or ""
            else:
                metadata[key] = element.get_attribute("content") or ""

        logger.debug("Collected metadata: %s", metadata)
        return metadata

    def validate(self, expected=None):
        expected = expected or {}
        metadata = self.get_metadata()
        errors = []

        for field, expected_value in expected.items():
            if not expected_value:
                continue
            actual = metadata.get(field, "")
            if not texts_match(expected_value, actual):
                errors.append(
                    f"{field}: expected '{expected_value}' in '{actual}'"
                )

        required_fields = ["title"]
        for field in required_fields:
            if not metadata.get(field):
                errors.append(f"{field} is empty")

        if errors:
            return False, "; ".join(errors), metadata

        logger.info("Metadata validation passed")
        return True, "Metadata validation passed", metadata
