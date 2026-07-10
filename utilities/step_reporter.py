"""Capture screenshots, Allure steps, and Excel validation rows."""

import re

import allure

from utilities.screenshot_util import ScreenshotUtil
from utilities.test_result_store import TestResultStore


def _slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return slug[:max_len] or "step"


class StepReporter:
    """Wraps each manual test step with Allure reporting, screenshot, and Excel rows."""

    def __init__(self, page, test_id: str, capture_screenshots: bool = True):
        self.page = page
        self.test_id = test_id
        self.capture_screenshots = capture_screenshots
        self.screenshot_util = ScreenshotUtil(page)
        self._current_step = 0
        self._current_title = ""

    def run(self, step_num: int, title: str, action=None, *, record_pass: bool = True):
        """Execute a step; optionally record a generic PASS row when action succeeds."""
        self._current_step = step_num
        self._current_title = title
        label = f"Step {step_num:02d}: {title}"
        with allure.step(label):
            try:
                result = action() if action else None
                if self.capture_screenshots:
                    name = f"{self.test_id}_step_{step_num:02d}_{_slug(title)}"
                    self.screenshot_util.capture(
                        name=name,
                        full_page=True,
                        subdir=self.test_id,
                    )
                if record_pass and action is not None:
                    self.record_check(
                        step_num=step_num,
                        step_title=title,
                        field_name="Step execution",
                        expected="Step completes without error",
                        actual="Step completed",
                        passed=True,
                    )
                return result
            except Exception as exc:
                self.record_check(
                    step_num=step_num,
                    step_title=title,
                    field_name="Step execution",
                    expected="Step completes without error",
                    actual=str(exc)[:500],
                    passed=False,
                    message=str(exc),
                )
                raise

    def record_check(
        self,
        *,
        step_num: int | None = None,
        step_title: str | None = None,
        field_name: str,
        expected: str,
        actual: str,
        passed: bool,
        message: str = "",
        status: str | None = None,
    ):
        TestResultStore.add_validation(
            step_num=step_num if step_num is not None else self._current_step,
            step_title=step_title or self._current_title,
            field_name=field_name,
            expected=expected,
            actual=actual,
            passed=passed,
            message=message,
            status=status,
            test_id=self.test_id,
        )

    def record_warning(
        self,
        *,
        step_num: int | None = None,
        step_title: str | None = None,
        field_name: str,
        expected: str,
        actual: str,
        message: str = "",
    ):
        self.record_check(
            step_num=step_num,
            step_title=step_title,
            field_name=field_name,
            expected=expected,
            actual=actual,
            passed=True,
            message=message,
            status="WARNING",
        )
