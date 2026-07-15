"""Post-process partner_products.xlsx: fill NaNs, fix trademark glyphs, light AI OCR fixes."""

from pathlib import Path
import json
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "testdata" / "partner_products.xlsx"
JSON = ROOT / "testdata" / "_ticket_extract.json"


def fix_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    # Common decode/replacement issues from ticket HTML
    replacements = {
        "Intel�": "Intel®",
        "Xeon�": "Xeon®",
        "Core�": "Core™",
        "vPro�": "vPro®",
        "Arc�": "Arc™",
        "�": "",  # leftover replacement chars
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    # Ticket content often uses a special AI character that became "Al"
    # Fix word-boundary Al -> AI when clearly meaning Artificial Intelligence
    text = re.sub(r"\bAl\b", "AI", text)
    text = re.sub(r"\bAl-", "AI-", text)
    return text.strip()


def main():
    df = pd.read_excel(XLSX, sheet_name="PartnerProducts")
    for col in df.columns:
        if col in ("enabled", "validate_pdf"):
            df[col] = df[col].fillna(False).astype(bool)
            continue
        if col == "expected_pdf_text":
            df[col] = ""
            continue
        df[col] = df[col].map(fix_text)

    # Ensure required columns order
    cols = [
        "enabled",
        "test_id",
        "ticket_number",
        "partner_name",
        "partner_dropdown_label",
        "product_name",
        "product_type",
        "search_term",
        "expected_title",
        "expected_short_description",
        "expected_description",
        "expected_meta_description",
        "expected_keywords",
        "expected_features",
        "expected_categories",
        "category_subcategory",
        "expected_contact_url",
        "expected_resource_url",
        "validate_pdf",
        "expected_pdf_text",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    # Keep search/title synced with cleaned product_name
    df["search_term"] = df["product_name"]
    df["expected_title"] = df.apply(
        lambda r: r["expected_title"] or r["product_name"], axis=1
    )
    df["partner_dropdown_label"] = df.apply(
        lambda r: r["partner_dropdown_label"] or r["partner_name"], axis=1
    )
    df["expected_categories"] = df["category_subcategory"]
    df["validate_pdf"] = False
    df["enabled"] = True

    with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PartnerProducts", index=False)

    print(f"Updated {XLSX}")
    print(df[["test_id", "partner_name", "product_name", "product_type"]].to_string(index=False))
    # sample check
    r = df[df["test_id"] == "PS-008"].iloc[0]
    print("PS-008 product:", r["product_name"])
    print("PS-004 contact:", df[df["test_id"] == "PS-004"].iloc[0]["expected_contact_url"])
    print("PS-001 intel tech:", df[df["test_id"] == "PS-001"].iloc[0]["category_subcategory"])


if __name__ == "__main__":
    main()
