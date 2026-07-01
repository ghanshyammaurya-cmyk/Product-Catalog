"""Add sample multi-product rows to partner_products.xlsx."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "testdata",
    "partner_products.xlsx",
)

NEW_ROWS = [
    {
        "enabled": True,
        "test_id": "PS-002",
        "partner_name": "ASUS",
        "product_name": "ASUS NUC 15 Pro+",
        "application_name": "ASUS NUC 15 Pro+",
        "product_type": "system",
        "search_term": "ASUS NUC 15 Pro+",
        "expected_title": "ASUS NUC 15 Pro+",
        "expected_short_description": "NUC",
        "expected_description": "NUC 15 Pro",
        "expected_breadcrumb": "Engagement > Solution Hub > Edge AI Catalog > Edge AI Partner Spotlight > ASUS NUC 15 Pro+",
        "expected_meta_description": "NUC",
        "expected_og_title": "ASUS NUC 15 Pro+",
        "expected_keywords": "",
        "expected_features": "",
        "expected_categories": "",
        "expected_contact_url": "asus",
        "validate_pdf": False,
        "expected_pdf_text": "",
        "category_subcategory": "",
    },
    {
        "enabled": True,
        "test_id": "PS-003",
        "partner_name": "Vecow",
        "product_name": "Vecow ECX-3200",
        "application_name": "Vecow ECX-3200",
        "product_type": "system",
        "search_term": "Vecow ECX-3200",
        "expected_title": "Vecow ECX-3200",
        "expected_short_description": "ECX",
        "expected_description": "ECX-3200",
        "expected_breadcrumb": "Engagement > Solution Hub > Edge AI Catalog > Edge AI Partner Spotlight > Vecow ECX-3200",
        "expected_meta_description": "ECX",
        "expected_og_title": "Vecow ECX-3200",
        "expected_keywords": "",
        "expected_features": "",
        "expected_categories": "",
        "expected_contact_url": "vecow",
        "validate_pdf": False,
        "expected_pdf_text": "",
        "category_subcategory": "",
    },
]

df = pd.read_excel(PATH)
existing_ids = set(df["test_id"].astype(str))
to_add = [row for row in NEW_ROWS if row["test_id"] not in existing_ids]
if to_add:
    df = pd.concat([df, pd.DataFrame(to_add)], ignore_index=True)
    with pd.ExcelWriter(PATH, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PartnerProducts", index=False)
    print(f"Added {len(to_add)} row(s): {[r['test_id'] for r in to_add]}")
else:
    print("PS-002 and PS-003 already exist — no changes")

print(f"Total enabled-ready rows: {len(df)}")
