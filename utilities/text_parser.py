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
    """Parse numbered or newline-separated feature list."""
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    text = str(value).strip()
    features = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        line = line.replace("x", " ").strip()
        if line and len(line) > 3:
            features.append(line)
    return features
