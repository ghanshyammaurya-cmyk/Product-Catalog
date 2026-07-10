"""Sanitize values before writing Excel workbooks (Excel-safe strings)."""

from __future__ import annotations

import math
import re
from typing import Any

# XML 1.0 illegal control characters (Excel OOXML rejects these)
_ILLEGAL_XML_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFE\uFFFF]")

# Characters that make Excel treat a cell as a formula when at the start
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_excel_value(value: Any, max_len: int = 32000) -> str | int | float | bool:
    """
    Make a value safe for .xlsx cells:
    - no illegal XML control chars
    - no formula injection (=, +, -, @ at start)
    - no NaN/None
    - length capped for Excel limit (32,767)
    """
    if value is None:
        return ""

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return value

    text = str(value)
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"):
        text = text.replace(ch, " ")
    text = text.replace("\ufffd", "'")
    text = _ILLEGAL_XML_RE.sub("", text)
    text = text.strip("\x00")

    if text and text[0] in _FORMULA_PREFIXES:
        text = f"'{text}"

    if len(text) > max_len:
        text = text[: max_len - 3] + "..."

    return text


def sanitize_dataframe(df):
    """Return a copy of df with all cells sanitized for Excel."""
    import pandas as pd

    if df is None or df.empty:
        return df

    clean = df.copy()
    for col in clean.columns:
        clean[col] = clean[col].map(sanitize_excel_value)
    return clean
