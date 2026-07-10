"""In-memory store for test validations — exported to Excel after the run."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from utilities.category_parser import pair_to_ticket_line
from utilities.excel_sanitize import sanitize_excel_value


@dataclass
class ValidationRecord:
    test_id: str
    test_name: str
    module: str
    step_num: int
    step_title: str
    field_name: str
    expected: str
    actual: str
    status: str  # PASS | FAIL | WARNING | SKIP
    message: str = ""
    partner: str = ""
    product: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class RunTestSummary:
    test_id: str
    test_name: str
    module: str
    partner: str
    product: str
    status: str  # PASSED | FAILED | SKIPPED | ERROR
    duration_sec: float
    failure_message: str = ""
    screenshot: str = ""


class TestResultStore:
    """Thread-safe collector for Excel export (supports pytest-xdist workers)."""

    _lock = threading.Lock()
    _context: dict[str, Any] = {}
    _validations: list[ValidationRecord] = []
    _summaries: list[RunTestSummary] = []
    _session_meta: dict[str, Any] = {}

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._context = {}
            cls._validations = []
            cls._summaries = []
            cls._session_meta = {}

    @classmethod
    def set_session_meta(cls, **kwargs):
        with cls._lock:
            cls._session_meta.update(kwargs)

    @classmethod
    def get_session_meta(cls) -> dict[str, Any]:
        with cls._lock:
            return dict(cls._session_meta)

    @classmethod
    def set_context(
        cls,
        *,
        test_id: str = "",
        test_name: str = "",
        module: str = "",
        partner: str = "",
        product: str = "",
    ):
        with cls._lock:
            cls._context = {
                "test_id": test_id or "N/A",
                "test_name": test_name or "",
                "module": module or "",
                "partner": partner or "",
                "product": product or "",
            }

    @classmethod
    def get_context(cls) -> dict[str, Any]:
        with cls._lock:
            return dict(cls._context)

    @classmethod
    def add_validation(
        cls,
        *,
        step_num: int,
        step_title: str,
        field_name: str,
        expected: str,
        actual: str,
        passed: bool,
        message: str = "",
        status: str | None = None,
        test_id: str | None = None,
        test_name: str | None = None,
        module: str | None = None,
        partner: str | None = None,
        product: str | None = None,
    ):
        ctx = cls.get_context()
        resolved_status = status or ("PASS" if passed else "FAIL")
        record = ValidationRecord(
            test_id=test_id or ctx.get("test_id", "N/A"),
            test_name=test_name or ctx.get("test_name", ""),
            module=module or ctx.get("module", ""),
            partner=partner or ctx.get("partner", ""),
            product=product or ctx.get("product", ""),
            step_num=step_num,
            step_title=sanitize_excel_value(step_title),
            field_name=sanitize_excel_value(field_name),
            expected=sanitize_excel_value(expected),
            actual=sanitize_excel_value(actual),
            status=resolved_status,
            message=sanitize_excel_value(message),
        )
        with cls._lock:
            cls._validations.append(record)

    @classmethod
    def add_category_pair_results(
        cls,
        *,
        step_num: int,
        step_title: str,
        pairs: list[dict],
        found: list[dict],
        missing: list[dict],
        site_tags: list | None = None,
    ):
        found_set = {
            (p.get("category", ""), p.get("subcategory", "")) for p in (found or [])
        }
        tags_preview = ", ".join((site_tags or [])[:8])
        for pair in pairs or []:
            cat = pair.get("category", "")
            sub = pair.get("subcategory", "")
            ok = (cat, sub) in found_set
            ticket_line = pair_to_ticket_line({"category": cat, "subcategory": sub})
            cls.add_validation(
                step_num=step_num,
                step_title=step_title,
                field_name="category_subcategory",
                expected=ticket_line,
                actual="Present on site" if ok else "Not found on site",
                passed=ok,
                message=(
                    f"'{ticket_line}' verified on listing + detail"
                    if ok
                    else f"'{ticket_line}' missing from site. Tags sampled: {tags_preview}"
                ),
            )

    @classmethod
    def add_contact_results(
        cls,
        *,
        step_num: int,
        step_title: str,
        fragments: list[str],
        matched: list[str],
        missing: list[str],
        links: list[dict] | None = None,
    ):
        matched_set = set(matched or [])
        on_page = ", ".join(
            (link.get("resolved") or link.get("href") or link.get("text") or "")[:80]
            for link in (links or [])[:3]
        )
        for fragment in fragments or []:
            ok = fragment in matched_set
            cls.add_validation(
                step_num=step_num,
                step_title=step_title,
                field_name="expected_contact_url",
                expected=fragment,
                actual=on_page if ok else f"Not matched. On page: {on_page}",
                passed=ok,
                message=(
                    f"Contact fragment '{fragment}' matched on detail page"
                    if ok
                    else f"Contact fragment '{fragment}' not found on detail page"
                ),
            )

    @classmethod
    def add_feature_results(
        cls,
        *,
        step_num: int,
        step_title: str,
        features: list[str],
        found: list[str],
        missing: list[str],
        section_preview: str = "",
    ):
        found_set = set(found or [])
        preview = (section_preview or "")[:200]
        for feature in features or []:
            ok = feature in found_set
            cls.add_validation(
                step_num=step_num,
                step_title=step_title,
                field_name=f"Feature: {feature}",
                expected=feature,
                actual="Present on detail page" if ok else "Not found on detail page",
                passed=ok,
                message=(
                    f"Feature '{feature}' verified in Features section"
                    if ok
                    else f"Feature '{feature}' missing. Section preview: {preview}"
                ),
            )

    @classmethod
    def record_test_outcome(
        cls,
        *,
        test_id: str,
        test_name: str,
        module: str,
        partner: str,
        product: str,
        status: str,
        duration_sec: float,
        failure_message: str = "",
        screenshot: str = "",
    ):
        summary = RunTestSummary(
            test_id=sanitize_excel_value(test_id or "N/A"),
            test_name=sanitize_excel_value(test_name),
            module=sanitize_excel_value(module),
            partner=sanitize_excel_value(partner),
            product=sanitize_excel_value(product),
            status=status,
            duration_sec=round(duration_sec, 2),
            failure_message=sanitize_excel_value((failure_message or "")[:2000]),
            screenshot=sanitize_excel_value(screenshot or ""),
        )
        with cls._lock:
            cls._summaries.append(summary)

    @classmethod
    def get_validations(cls) -> list[ValidationRecord]:
        with cls._lock:
            return list(cls._validations)

    @classmethod
    def get_summaries(cls) -> list[RunTestSummary]:
        with cls._lock:
            return list(cls._summaries)
