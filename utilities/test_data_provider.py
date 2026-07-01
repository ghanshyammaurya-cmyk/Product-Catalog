import os

import pytest

from utilities.excel_reader import ExcelReader
from utilities.logger import get_logger

logger = get_logger(__name__)


def load_partner_product_data():
    reader = ExcelReader()
    if not os.path.exists(reader.file_path):
        logger.warning("Test data file not found: %s", reader.file_path)
        return []
    return reader.get_partner_products()


def partner_product_ids(data):
    return data.get("test_id") or data.get("product_name") or "unnamed_test"


def pytest_generate_tests(metafunc):
    """Optional hook for dynamic parametrization via marker."""
    if "excel_row" in metafunc.fixturenames:
        marker = metafunc.definition.get_closest_marker("excel_data")
        sheet = marker.kwargs.get("sheet") if marker else None
        reader = ExcelReader(sheet_name=sheet) if sheet else ExcelReader()
        if not os.path.exists(reader.file_path):
            pytest.skip(f"Test data file not found: {reader.file_path}")
        rows = reader.get_partner_products()
        ids = [partner_product_ids(row) for row in rows]
        metafunc.parametrize("excel_row", rows, ids=ids)
