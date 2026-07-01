from playwright.sync_api import Page

from utilities.constants import PARTNER_LOGO_SELECTORS
from utilities.logger import get_logger

logger = get_logger(__name__)


class LogoValidator:
    """Validates partner logo visibility on builders.intel.com product pages."""

    def __init__(self, page: Page):
        self.page = page

    def find_logo(self, partner_name=None):
        for selector in PARTNER_LOGO_SELECTORS:
            logos = self.page.locator(selector)
            for index in range(logos.count()):
                logo = logos.nth(index)
                try:
                    if not logo.is_visible(timeout=2000):
                        continue
                except Exception:
                    continue

                alt = (logo.get_attribute("alt") or "").strip()
                src = (logo.get_attribute("src") or "").strip()

                if "intel" in alt.lower() and "logo" in alt.lower():
                    continue

                if partner_name:
                    name_match = (
                        partner_name.lower() in alt.lower()
                        or partner_name.lower() in src.lower()
                        or "companylogo" in src.lower()
                    )
                    if not name_match and "companylogo" not in src.lower():
                        continue

                if src or alt:
                    return logo, {"alt": alt, "src": src, "selector": selector}

        return None, {}

    def validate(self, partner_name=None, min_width=1, min_height=1):
        logo, info = self.find_logo(partner_name)
        if logo is None:
            return False, f"Partner logo not found for: {partner_name or 'partner'}", info

        box = logo.bounding_box()
        if not box:
            return False, "Logo has no bounding box", info

        if box["width"] < min_width or box["height"] < min_height:
            return (
                False,
                f"Logo dimensions too small: {box['width']}x{box['height']}",
                info,
            )

        src = info.get("src", "")
        if not src:
            return False, "Logo src attribute is empty", info

        natural_width = logo.evaluate("el => el.naturalWidth")
        natural_height = logo.evaluate("el => el.naturalHeight")
        if natural_width == 0 or natural_height == 0:
            return False, "Logo image failed to load (natural size is 0)", info

        logger.info("Logo validation passed for %s", partner_name or "partner")
        return True, "Logo validation passed", {**info, "box": box}
