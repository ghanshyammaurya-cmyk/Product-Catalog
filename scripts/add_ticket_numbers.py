"""Add the source WebSupport ticket number to partner_products.xlsx."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "testdata" / "partner_products.xlsx"

TICKET_BY_TEST_ID = {
    "PS-001": 25102,
    "PS-002": 25122,
    "PS-003": 25123,
    "PS-004": 25103,
    "PS-005": 25101,
    "PS-006": 25104,
    "PS-007": 25116,
    "PS-008": 25106,
    "PS-009": 25107,
    "PS-010": 25108,
    "PS-011": 25109,
    "PS-012": 25110,
    "PS-013": 25111,
    "PS-014": 25112,
    "PS-015": 25113,
    "PS-016": 25114,
}


def main():
    df = pd.read_excel(XLSX, sheet_name="PartnerProducts", keep_default_na=False)
    df["ticket_number"] = df["test_id"].map(TICKET_BY_TEST_ID).fillna("")

    columns = list(df.columns)
    columns.remove("ticket_number")
    test_id_index = columns.index("test_id")
    columns.insert(test_id_index + 1, "ticket_number")
    df = df[columns]

    with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PartnerProducts", index=False)

    print(df[["test_id", "ticket_number", "partner_name", "product_name"]].to_string(index=False))


if __name__ == "__main__":
    main()
