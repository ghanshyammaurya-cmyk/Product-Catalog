"""Capture screenshots and Allure steps for the 26-step manual test flow."""

import re

import allure

from utilities.screenshot_util import ScreenshotUtil


def _slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return slug[:max_len] or "step"


class StepReporter:
    """Wraps each manual test step with Allure reporting and a screenshot."""

    def __init__(self, page, test_id: str, capture_screenshots: bool = True):
        self.page = page
        self.test_id = test_id
        self.capture_screenshots = capture_screenshots
        self.screenshot_util = ScreenshotUtil(page)

    def run(self, step_num: int, title: str, action=None):
        label = f"Step {step_num:02d}: {title}"
        with allure.step(label):
            result = action() if action else None
            if self.capture_screenshots:
                name = f"{self.test_id}_step_{step_num:02d}_{_slug(title)}"
                self.screenshot_util.capture(
                    name=name,
                    full_page=True,
                    subdir=self.test_id,
                )
            return result
