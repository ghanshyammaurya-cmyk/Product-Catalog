"""Shared test helpers for parsing Excel-driven flags and expected values."""

from utilities.category_parser import (
    format_category_subcategory_report,
    parse_category_subcategory as _parse_cat_sub,
    parse_category_subcategory_pairs,
    parse_ticket_sections,
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
    return str(value).strip()


def parse_breadcrumb_trail(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("/", ">")
    return [part.strip() for part in text.split(">") if part.strip()]


def parse_category_subcategory(data):
    return _parse_cat_sub(data)


def format_category_subcategory(data):
    """Display value for reports — Category / Sub Category lines from Excel."""
    category = get_str(data, "category")
    subcategory = get_str(data, "subcategory")
    if category and subcategory:
        pairs = [{"category": category, "subcategory": subcategory}]
        extra = parse_category_subcategory_pairs(get_str(data, "category_subcategory"))
        if extra:
            pairs = extra
        return format_category_subcategory_report(pairs)

    combined = get_str(data, "category_subcategory")
    if combined:
        pairs = parse_category_subcategory_pairs(combined)
        if pairs:
            return format_category_subcategory_report(pairs)
        return combined
    return category or subcategory or ""


def get_category_subcategory_pairs(data):
    """All Category / Sub Category pairs from Excel row."""
    category = get_str(data, "category")
    subcategory = get_str(data, "subcategory")
    if category and subcategory:
        pairs = [{"category": category, "subcategory": subcategory}]
    else:
        pairs = []

    combined = get_str(data, "category_subcategory")
    if combined:
        ticket_pairs = parse_category_subcategory_pairs(combined)
        if ticket_pairs:
            return ticket_pairs
    return pairs


def parse_expected_categories(value):
    """Parse multi-line category spec into individual terms to verify."""
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return []

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
