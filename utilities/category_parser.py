"""Parse category_subcategory column for filter application."""

import re

# Sidebar section headers from client ticket format (Application Categories & Sub-Categories)
TICKET_SECTION_HEADERS = {
    "device type",
    "vertical",
    "use cases",
    "vertical use cases",
    "open software platform",
    "intel technologies",
    "intel technologies and platforms",
    "intel processors",
    "intel graphics",
    "geo availability",
    "geographical availability",
    "target audience",
    "edge ai application",
    "edge ai system",
}

# Ticket sections that exist as expandable groups in the Partner Spotlight sidebar
SIDEBAR_FILTER_SECTIONS = {
    "device type",
    "vertical",
    "verticals",
    "use cases",
    "vertical use cases",
    "open software platform",
    "intel open software platform",
    "intel technologies",
    "intel technologies and platforms",
    "intel processors",
    "intel graphics",
    "geo availability",
    "geographical availability",
    "target audience",
    "edge feature",
    "edge features",
    "ai edge system sizing",
}

# Ticket wording may differ from the current Partner Spotlight UI. Preserve the
# ticket text in Excel/reporting, but use these canonical labels for UI actions.
_SECTION_ALIASES = {
    "intel processors": "Intel Technologies and Platforms",
    "intel graphics": "Intel Technologies and Platforms",
    "intel technologies": "Intel Technologies and Platforms",
    "intel technologies and platforms": "Intel Technologies and Platforms",
    "vertical": "Verticals",
    "verticals": "Verticals",
    "use cases": "Vertical Use Cases",
    "vertical use cases": "Vertical Use Cases",
    "open software platform": "Intel Open Software Platform",
    "intel open software platform": "Intel Open Software Platform",
    "geo availability": "Geographical Availability",
    "geographical availability": "Geographical Availability",
    "edge feature": "Edge Features",
    "edge features": "Edge Features",
}

_VALUE_ALIASES = {
    "health & life sciences": "Healthcare and Life Sciences",
    "health life sciences": "Healthcare and Life Sciences",
    "health and life sciences": "Healthcare and Life Sciences",
    "openvino tool kit": "OpenVINO™ Toolkit",
    "openvino toolkit": "OpenVINO™ Toolkit",
    "real-time": "Real-time",
    "real time": "Real-time",
    # Exact ticket → site labels (System / Application screenshots)
    "intel core ultra series 3 processors": "Intel® Core™ Ultra Series 3 processors",
    "intel core ultra series 2 processors": "Intel® Core™ Ultra Series 2 processors",
    "intel core processors (series 1)": "Intel® Core™ processors (Series 1)",
    "intel core processors (series 2)": "Intel® Core™ processors (Series 2)",
    "13th gen intel core processors": "13th Gen Intel® Core™ processors",
    "14th gen intel core processors": "14th Gen Intel® Core™ processors",
    "intel arc pro b-series graphics": "Intel® Arc™ Pro B-Series Graphics",
    "intel arc pro b series graphics": "Intel® Arc™ Pro B-Series Graphics",
    "intel arc b-series graphics": "Intel® Arc™ B-Series Graphics",
    "intel arc b series graphics": "Intel® Arc™ B-Series Graphics",
    "intel iris xe graphics": "Intel® Iris® Xe Graphics",
}


def _alias_lookup_key(value: str) -> str:
    key = value.lower().replace("®", "").replace("™", "")
    key = re.sub(r"\s+", " ", key).strip()
    key = re.sub(r"\b5ht\s+gen\b", "5th gen", key)
    return key


def canonical_section_name(section_name):
    """Map ticket category headings to current site sidebar headings."""
    text = normalize_ticket_text(section_name).strip()
    return _SECTION_ALIASES.get(text.lower(), text)


def canonical_subcategory_value(value):
    """Map ticket sub-category spelling/trademark variants to current site labels."""
    text = normalize_ticket_text(value).strip()
    if not text:
        return ""

    # Common ticket typo: "5ht Gen" should match site's "5th Gen".
    text = re.sub(r"\b5ht\s+Gen\b", "5th Gen", text, flags=re.I)
    key = _alias_lookup_key(text)

    if key in _VALUE_ALIASES:
        return _VALUE_ALIASES[key]

    # Apply Intel trademark conventions from System/Application category UI.
    # Order matters: more specific phrases first.
    replacements = [
        (r"\bIntel\s+Core\s+Ultra\s+Series\s+(\d+)\s+processors\b",
         r"Intel® Core™ Ultra Series \1 processors"),
        (r"\bIntel\s+Core\s+Ultra\s+processors\s*\(\s*Series\s+(\d+)\s*\)",
         r"Intel® Core™ Ultra processors (Series \1)"),
        (r"\bIntel\s+Core\s+Ultra\s+processors\b",
         r"Intel® Core™ Ultra processors"),
        (r"\b(\d+)(?:st|nd|rd|th)\s+Gen\s+Intel\s+Core\s+processors\b",
         r"\1th Gen Intel® Core™ processors"),
        (r"\bIntel\s+Core\s+processors\s*\(\s*Series\s+(\d+)\s*\)",
         r"Intel® Core™ processors (Series \1)"),
        (r"\bIntel\s+Core\s+processors\b",
         r"Intel® Core™ processors"),
        (r"\bIntel\s+Arc\s+Pro\s+B[-\s]?Series\s+Graphics\b",
         r"Intel® Arc™ Pro B-Series Graphics"),
        (r"\bIntel\s+Arc\s+B[-\s]?Series\s+Graphics\b",
         r"Intel® Arc™ B-Series Graphics"),
        (r"\bIntel\s+Arc\s+Pro\s+A[-\s]?Series\s+Graphics\b",
         r"Intel® Arc™ Pro A-Series Graphics"),
        (r"\bIntel\s+Arc\s+A[-\s]?Series\s+Graphics\b",
         r"Intel® Arc™ A-Series Graphics"),
        (r"\bIntel\s+Iris\s+Xe\s+Graphics\b",
         r"Intel® Iris® Xe Graphics"),
        (r"\bIntel\s+Xeon\s+(\d+)\s+[Pp]rocessors\b",
         r"Intel® Xeon® \1 processors"),
        (r"\b(\d+)(?:st|nd|rd|th)\s+Gen\s+Intel\s+Xeon\s+Scalable\s+processors\b",
         r"\1th Gen Intel® Xeon® Scalable processors"),
        (r"\bIntel\s+Xeon\s+Scalable\s+processors\b",
         r"Intel® Xeon® Scalable processors"),
        (r"\bIntel\s+Xeon\s+([WED])\s+processor\b",
         r"Intel® Xeon® \1 processor"),
        (r"\bIntel\s+Xeon\s+processors\b",
         r"Intel® Xeon® processors"),
        (r"\bIntel\s+Atom\s+processor\b",
         r"Intel® Atom® processor"),
        (r"\bIntel\s+Pentium\s+processors\b",
         r"Intel® Pentium® processors"),
        (r"\bIntel\s+Celeron\s+processors\b",
         r"Intel® Celeron® processors"),
        (r"\bIntel\s+Gaudi\s+AI\s+Accelerators\b",
         r"Intel® Gaudi® AI Accelerators"),
        (r"\bOpenVINO\s+Tool\s*Kit\b",
         r"OpenVINO™ Toolkit"),
        (r"\bOpenVINO\s+Toolkit\b",
         r"OpenVINO™ Toolkit"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.I)

    # Normalize hyphen/space variants already carrying trademarks.
    text = re.sub(
        r"Intel®\s+Arc™\s+Pro\s+B\s+Series\s+Graphics",
        "Intel® Arc™ Pro B-Series Graphics",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"Intel®\s+Arc™\s+B\s+Series\s+Graphics",
        "Intel® Arc™ B-Series Graphics",
        text,
        flags=re.I,
    )
    # Site/ticket label uses hyphenated "Real-time"
    text = re.sub(r"\bReal\s+time\b", "Real-time", text, flags=re.I)
    # Keep processor casing consistent with site labels
    text = re.sub(r"\bProcessors\b", "processors", text)
    text = re.sub(r"\bGraphics\b", "Graphics", text)
    return text


def normalize_ticket_text(value):
    """Strip zero-width and odd unicode spaces from Excel/ticket paste."""
    if value is None:
        return ""
    text = str(value)
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"):
        text = text.replace(ch, " ")
    return re.sub(r"\s+", " ", text).strip() if "\n" not in text else text.replace("\u200b", "").replace("\ufeff", "")


def _split_ticket_values(rest):
    """Split ticket values on , or ; but not inside parentheses."""
    values = []
    current = []
    depth = 0
    for ch in rest:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            val = normalize_ticket_text("".join(current))
            if val and val.upper() != "TBC":
                values.append(val)
            current = []
        else:
            current.append(ch)
    val = normalize_ticket_text("".join(current))
    if val and val.upper() != "TBC":
        values.append(val)
    return values


def parse_ticket_sections(value):
    """
    Parse client ticket multi-line format into sidebar sections and values.

    Example:
        Device Type: Edge Device
        Vertical: Retail
    """
    if not value or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    combined = normalize_ticket_text(value).strip()
    sections = []

    if ">" in combined and "\n" not in combined and ":" not in combined:
        category, rest = combined.split(">", 1)
        values = [s.strip() for s in rest.replace("|", ",").split(",") if s.strip()]
        if category.strip():
            sections.append({"section": category.strip(), "values": values})
        return sections

    for line in combined.split("\n"):
        line = line.strip()
        if not line or line.upper() == "TBC":
            continue
        if ":" not in line:
            continue
        label, rest = line.split(":", 1)
        section = label.strip()
        if section.lower() in ("geo availability", "geographical availability"):
            values = [
                normalize_ticket_text(v)
                for v in rest.split(";")
                if normalize_ticket_text(v) and normalize_ticket_text(v).upper() != "TBC"
            ]
        else:
            values = _split_ticket_values(rest)
        if section and values:
            sections.append({"section": section, "values": values})

    return sections


def parse_category_subcategory_pairs(value, *, canonicalize=True):
    """
    Flat list of Category / Sub Category pairs for reporting and filter application.

    Returns: [{"category": "Verticals", "subcategory": "Retail"}, ...]
    When canonicalize=True, section and value labels are mapped to site naming
    (including Intel ® / ™ trademarks).
    """
    pairs = []
    for sec in parse_ticket_sections(value):
        category = (
            canonical_section_name(sec["section"]) if canonicalize else sec["section"]
        )
        for val in sec["values"]:
            subcategory = (
                canonical_subcategory_value(val) if canonicalize else val
            )
            pairs.append({"category": category, "subcategory": subcategory})
    return pairs


def _is_sidebar_section(section_name):
    return section_name.strip().lower() in SIDEBAR_FILTER_SECTIONS or any(
        key in section_name.strip().lower() for key in SIDEBAR_FILTER_SECTIONS
    )


def sidebar_section_label(section_name):
    """Map ticket/Excel section names to Partner Spotlight sidebar labels."""
    return canonical_section_name(section_name)


def parse_sidebar_filter_sections(value, values_per_section=None):
    """
    All sidebar-applicable category/sub-category groups from the ticket.
    When values_per_section is None, every sub-category from Excel is included.
    """
    sections = parse_ticket_sections(value)
    if not sections:
        return []

    priority = (
        "device type",
        "vertical",
        "verticals",
        "use cases",
        "vertical use cases",
        "open software platform",
        "intel technologies",
        "geo availability",
        "geographical availability",
        "target audience",
    )
    ranked = sorted(
        sections,
        key=lambda s: (
            next(
                (i for i, p in enumerate(priority) if p in s["section"].lower()),
                99,
            ),
            s["section"].lower(),
        ),
    )

    sidebar_sections = []
    for sec in ranked:
        if not _is_sidebar_section(sec["section"]):
            continue
        if values_per_section is None:
            values = list(sec["values"])
        else:
            values = sec["values"][: max(1, values_per_section)]
        sidebar_sections.append(
            {
                "section": sec["section"],
                "sidebar_label": sidebar_section_label(sec["section"]),
                "values": [canonical_subcategory_value(value) for value in values],
            }
        )
    return sidebar_sections


def parse_navigation_filter_sections(value):
    """Backward-compatible alias — all sub-categories per sidebar section."""
    return parse_sidebar_filter_sections(value, values_per_section=None)


def format_category_subcategory_report(pairs):
    """Human-readable Category / Sub Category block for logs and HTML report."""
    if not pairs:
        return "N/A"
    lines = [pair_to_ticket_line(p) for p in pairs]
    return "\n".join(lines)


def pair_to_ticket_line(pair):
    """Single ticket-style line: Vertical: Retail"""
    return f"{pair['category']}: {pair['subcategory']}"


def filter_result_key(category, subcategory):
    """Standard key used in logs and step results (ticket format)."""
    return pair_to_ticket_line({"category": category, "subcategory": subcategory})


def parse_primary_filter_values(value, max_values=3):
    """First N checkbox values to apply/verify (e.g. Edge Device, Retail)."""
    sections = parse_ticket_sections(value)
    values = []
    for sec in sections:
        for val in sec["values"]:
            if val.lower() not in {v.lower() for v in values}:
                values.append(val)
            if len(values) >= max_values:
                return values
    return values


def parse_filter_terms(value):
    """Extract individual sidebar filter terms from category_subcategory value."""
    if not value or str(value).strip() == "" or str(value).lower() == "nan":
        return []

    combined = str(value).strip()

    # Simple format: Category > Sub1, Sub2
    if ">" in combined and "\n" not in combined:
        category, rest = combined.split(">", 1)
        terms = [category.strip()]
        terms.extend(
            s.strip() for s in rest.replace("|", ",").split(",") if s.strip()
        )
        return _dedupe_terms(terms)

    # Multi-line ticket format (Edge Feature: ..., Vertical: ...)
    if "\n" in combined or (":" in combined and ">" not in combined):
        terms = []
        for line in combined.split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                label, rest = line.split(":", 1)
                section = label.strip()
                if section:
                    terms.append(section)
                for part in rest.replace(";", ",").split(","):
                    t = part.strip()
                    if t and len(t) > 2 and t.upper() != "TBC":
                        terms.append(t)
            else:
                for part in line.replace(";", ",").split(","):
                    t = part.strip()
                    if t and len(t) > 2 and t.upper() != "TBC":
                        terms.append(t)
        return _dedupe_terms(terms)

    parts = [s.strip() for s in combined.replace("|", ",").split(",") if s.strip()]
    return _dedupe_terms(parts)


def _dedupe_terms(terms):
    seen = set()
    unique = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def parse_category_subcategory_value(value):
    """Legacy: returns (category, [subcategories])."""
    terms = parse_filter_terms(value)
    if not terms:
        return "", []
    if len(terms) == 1:
        return "", terms
    return terms[0], terms[1:]


def parse_category_subcategory(data):
    """Parse from Excel row dict (single column or legacy columns)."""
    combined = data.get("category_subcategory")
    if combined is not None and str(combined).strip() and str(combined).lower() != "nan":
        return parse_category_subcategory_value(combined)

    category = str(data.get("category") or "").strip()
    subcategory = str(data.get("subcategory") or "").strip()
    subcategories = [
        s.strip()
        for s in subcategory.replace("|", ",").split(",")
        if s.strip()
    ] if subcategory else []
    return category, subcategories
