"""Parse client-provided text fields (features, categories, etc.)."""

import re
import unicodedata


def normalize_text(text):
    """Normalize unicode quotes/apostrophes for comparison."""
    if text is None:
        return ""
    text = str(text)
    for old, new in (
        ("\u2019", "'"),
        ("\u2018", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\ufffd", "'"),
    ):
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text).strip()


def texts_match(expected, actual, min_keyword_ratio=0.5):
    """Fuzzy match handling encoding differences and truncation."""
    expected_n = normalize_text(expected).lower()
    actual_n = normalize_text(actual).lower()
    if not expected_n:
        return True
    if expected_n in actual_n:
        return True
    keywords = [w for w in re.split(r"[\s,;]+", expected_n) if len(w) > 3]
    if not keywords:
        return expected_n in actual_n
    matched = sum(1 for w in keywords if w in actual_n)
    return matched >= max(2, int(len(keywords) * min_keyword_ratio))


def parse_expected_features(value):
    """Parse numbered, newline-, or semicolon-separated feature list."""
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    text = str(value).strip()
    features = []
    for line in re.split(r"[\n;]+", text):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        line = line.replace("x", " ").strip()
        if line and len(line) > 3:
            features.append(line)
    return features


def feature_on_site(expected_feature: str, haystack: str) -> bool:
    """Strict check: Excel feature text must appear on the product detail page."""
    if not expected_feature or not str(expected_feature).strip():
        return False

    expected = normalize_text(str(expected_feature)).lower()
    haystack_norm = normalize_text(haystack).lower()
    if not expected or not haystack_norm:
        return False

    if expected in haystack_norm:
        return True
    if expected.replace(" ", "") in haystack_norm.replace(" ", ""):
        return True

    words = [
        w
        for w in re.findall(r"[a-z0-9]+", expected)
        if len(w) >= 3 and w not in ("and", "the", "for", "with")
    ]
    if words and all(w in haystack_norm for w in words):
        return True

    return False


def parse_expected_contact_fragments(value):
    """
    Parse expected_contact_url — mailto, http(s), and domain fragments.

    Examples:
        mailto:patrick@dynamofl.com
        mailto:patrick@dynamofl.com; https://www.dynamofl.com/contact
    """
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    text = str(value).strip()
    fragments = []
    for part in re.split(r"[\n;|]+", text):
        for piece in part.split(","):
            piece = piece.strip()
            if piece:
                fragments.append(piece)
    return fragments
