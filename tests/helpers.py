"""Shared test helpers for parsing Excel-driven flags and expected values."""

from utilities.category_parser import (
    format_category_subcategory_report,
    parse_category_subcategory_pairs,
)
from utilities.text_parser import parse_expected_features as _parse_features


def as_bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("true", "yes", "1", "y")


def get_str(data, key, default=""):
    value = data.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    if text.lower() == "nan":
        return default
    return text


def parse_breadcrumb_trail(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("/", ">")
    return [part.strip() for part in text.split(">") if part.strip()]


def get_category_subcategory_raw(data):
    """Single Excel column: category_subcategory (ticket multi-line format)."""
    combined = get_str(data, "category_subcategory")
    if combined:
        return combined
    # Backward compatibility if sheet still uses expected_categories
    return get_str(data, "expected_categories")


def format_category_subcategory(data):
    """Display value for reports from category_subcategory column."""
    combined = get_category_subcategory_raw(data)
    if not combined:
        return ""
    pairs = parse_category_subcategory_pairs(combined)
    if pairs:
        return format_category_subcategory_report(pairs)
    return combined


def get_category_subcategory_pairs(data):
    """All category/sub-category pairs from category_subcategory column."""
    combined = get_category_subcategory_raw(data)
    if not combined:
        return []
    return parse_category_subcategory_pairs(combined)


def parse_category_subcategory(data):
    """Legacy alias — returns (category, [subcategories]) from category_subcategory."""
    from utilities.category_parser import parse_category_subcategory_value

    combined = get_category_subcategory_raw(data)
    if combined:
        return parse_category_subcategory_value(combined)
    return "", []


def parse_expected_categories(value):
    """Parse category_subcategory / expected_categories into individual terms."""
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    pairs = parse_category_subcategory_pairs(str(value))
    if pairs:
        terms = []
        for pair in pairs:
            terms.append(pair["category"])
            terms.append(pair["subcategory"])
        return terms

    text = str(value).strip()
    terms = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            _, rest = line.split(":", 1)
            parts = rest.replace(";", ",").split(",")
        else:
            parts = line.replace(";", ",").split(",")
        for part in parts:
            term = part.strip()
            if term and len(term) > 2 and term.upper() != "TBC":
                terms.append(term)

    if not terms and "," in text:
        terms = [p.strip() for p in text.split(",") if p.strip() and p.strip().upper() != "TBC"]

    return terms


def parse_expected_features(value):
    return _parse_features(value)


def parse_csv(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def build_metadata_expectations(data):
    expected = {}
    mapping = {
        "expected_title": "title",
        "expected_meta_description": "description",
        "expected_og_title": "og_title",
        "expected_keywords": "keywords",
        "product_name": "title",
    }
    for excel_key, meta_key in mapping.items():
        value = get_str(data, excel_key)
        if not value:
            continue
        if meta_key in expected:
            continue
        expected[meta_key] = value
    return expected or None
