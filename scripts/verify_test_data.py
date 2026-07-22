"""Quick completeness report for testdata/partner_products.xlsx."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "testdata" / "partner_products.xlsx"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

df = pd.read_excel(XLSX, sheet_name="PartnerProducts", keep_default_na=False)
print(f"Rows: {len(df)} | Enabled: {df['enabled'].sum()}")
print()
for r in df.itertuples():
    feats = [ln for ln in str(r.expected_features).splitlines() if ln.strip()]
    cats = [ln for ln in str(r.category_subcategory).splitlines() if ln.strip()]
    print(
        f"{r.test_id} | ticket {r.ticket_number} | {r.partner_name} | "
        f"{r.product_name} | {r.product_type}"
    )
    print(
        f"    desc={len(str(r.expected_description))} chars | "
        f"features={len(feats)} | categories={len(cats)} | "
        f"contact={'Y' if str(r.expected_contact_url).strip() else 'MISSING'} | "
        f"resource={'Y' if str(r.expected_resource_url).strip() else 'MISSING'} | "
        f"short_desc={'Y' if str(r.expected_short_description).strip() else 'MISSING'}"
    )
