"""Shared helpers for recording catalog-level validations in Excel."""

from utilities.test_result_store import TestResultStore


def record_catalog_check(
    *,
    test_id: str,
    step_num: int,
    step_title: str,
    field_name: str,
    expected: str,
    actual: str,
    passed: bool,
    message: str = "",
):
    TestResultStore.add_validation(
        test_id=test_id,
        test_name=TestResultStore.get_context().get("test_name", ""),
        module="Edge Catalog",
        step_num=step_num,
        step_title=step_title,
        field_name=field_name,
        expected=expected,
        actual=actual,
        passed=passed,
        message=message,
    )
