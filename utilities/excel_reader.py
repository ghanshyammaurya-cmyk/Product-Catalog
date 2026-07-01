import math
import os

import pandas as pd

from utilities.config_reader import ConfigReader
from utilities.logger import get_logger

logger = get_logger(__name__)


def is_row_enabled(value) -> bool:
    """Parse Excel enabled column: TRUE/FALSE, 1/0, true/false, yes/no."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return False
        return int(value) == 1

    text = str(value).strip().lower()
    if text in ("", "nan", "none", "false", "no", "n", "0", "0.0"):
        return False
    if text in ("true", "yes", "y", "t", "1", "1.0"):
        return True
    return False


class ExcelReader:
    def __init__(self, file_path=None, sheet_name=None):
        self.file_path = file_path or ConfigReader.get_path("testdata_path")
        self.sheet_name = sheet_name or ConfigReader.get("testdata_sheet", 0)

    def read_sheet(self, sheet_name=None):
        sheet = sheet_name if sheet_name is not None else self.sheet_name
        logger.debug("Reading Excel sheet '%s' from %s", sheet, self.file_path)
        return pd.read_excel(self.file_path, sheet_name=sheet)

    def get_rows(self, sheet_name=None, enabled_only=True):
        df = self.read_sheet(sheet_name)

        # Ignore blank template rows at the bottom of the sheet
        if "test_id" in df.columns:
            df = df[
                df["test_id"].notna()
                & (df["test_id"].astype(str).str.strip() != "")
                & (df["test_id"].astype(str).str.lower() != "nan")
            ]

        df = df.fillna("")

        if enabled_only and "enabled" in df.columns:
            before = len(df)
            df = df[df["enabled"].apply(is_row_enabled)]
            logger.info(
                "Excel filter: %d enabled row(s) of %d with test_id",
                len(df),
                before,
            )

        return df.to_dict(orient="records")

    def get_partner_products(self, sheet_name=None):
        return self.get_rows(sheet_name)

    def get_test_ids(self, sheet_name=None):
        rows = self.get_rows(sheet_name)
        return [row.get("test_id") or row.get("product_name", f"row_{i}") for i, row in enumerate(rows)]
