import os
from datetime import datetime

import allure

from utilities.config_reader import ConfigReader
from utilities.logger import get_logger

logger = get_logger(__name__)


class ScreenshotUtil:
    def __init__(self, page):
        self.page = page
        self.screenshot_dir = ConfigReader.get_path("screenshot_path", "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def capture(self, name="screenshot", full_page=True, subdir=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{safe_name}_{timestamp}.png"
        target_dir = self.screenshot_dir
        if subdir:
            target_dir = os.path.join(self.screenshot_dir, subdir)
            os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        self.page.screenshot(path=filepath, full_page=full_page)
        logger.info("Screenshot saved: %s", filepath)
        self._attach_to_allure(filepath, name)
        return filepath

    @staticmethod
    def _attach_to_allure(filepath, name):
        try:
            with open(filepath, "rb") as image:
                allure.attach(
                    image.read(),
                    name=name,
                    attachment_type=allure.attachment_type.PNG,
                )
        except OSError:
            logger.warning("Could not attach screenshot to Allure: %s", filepath)
