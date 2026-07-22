"""Normalize category_subcategory / expected_categories to site trademarks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utilities.category_parser import (
    canonical_section_name,
    canonical_subcategory_value,
    parse_ticket_sections,
)

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "testdata" / "partner_products.xlsx"


def normalize_categories_block(raw: str) -> str:
    # Repair known ticket paste issues before parsing
    text = str(raw or "")
    text = text.replace(
        "US/CanadaAsia Pacific, Japan, Australia & New Zealand",
        "US/Canada; Asia Pacific, Japan, Australia & New Zealand",
    )
    text = text.replace(
        "US/CanadaAsia Pacific",
        "US/Canada; Asia Pacific",
    )

    sections = parse_ticket_sections(text)
    if not sections:
        return ""

    merged: dict[str, list[str]] = {}
    order: list[str] = []
    for sec in sections:
        section = canonical_section_name(sec["section"])
        if section not in merged:
            merged[section] = []
            order.append(section)
        for value in sec["values"]:
            canon = canonical_subcategory_value(value)
            if not canon:
                continue
            # Deduplicate by case-insensitive compare
            existing = {v.lower() for v in merged[section]}
            if canon.lower() not in existing:
                merged[section].append(canon)

    lines = []
    for section in order:
        values = merged[section]
        if not values:
            continue
        if section == "Geographical Availability":
            lines.append(f"{section}: {'; '.join(values)}")
        else:
            lines.append(f"{section}: {', '.join(values)}")
    return "\n".join(lines)


def main():
    df = pd.read_excel(XLSX, sheet_name="PartnerProducts", keep_default_na=False)
    for idx, row in df.iterrows():
        raw = row.get("category_subcategory") or row.get("expected_categories") or ""
        normalized = normalize_categories_block(str(raw))
        df.at[idx, "category_subcategory"] = normalized
        df.at[idx, "expected_categories"] = normalized

    with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PartnerProducts", index=False)

    print(f"Updated {XLSX}")
    for r in df.itertuples():
        print(f"\n=== {r.test_id} ({r.product_type}) ===")
        print(r.category_subcategory)


if __name__ == "__main__":
    main()
