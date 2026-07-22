from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from qa_tool.app import app
from qa_tool.services import TestDataService as DataService
from qa_tool.services import environment_summary


def test_dashboard_health_and_home():
    client = TestClient(app)

    health = client.get("/api/health")
    home = client.get("/")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert home.status_code == 200
    assert "EdgeQA Automation Console" in home.text


def test_environment_summary_exposes_demo_qa_and_live():
    environments = environment_summary()

    assert [item["id"] for item in environments] == ["demo", "qa", "live"]
    assert [item["framework_name"] for item in environments] == [
        "dev",
        "staging",
        "prod",
    ]


def test_test_data_service_validates_and_creates_backup(tmp_path: Path):
    workbook = tmp_path / "partner_products.xlsx"
    frame = pd.DataFrame(
        [
            {
                "enabled": True,
                "test_id": "PS-001",
                "ticket_number": "25102",
                "partner_name": "Partner",
                "partner_dropdown_label": "Partner",
                "product_name": "Product",
                "product_type": "application",
                "search_term": "Product",
                "validate_pdf": False,
            }
        ]
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="PartnerProducts", index=False)

    service = DataService(workbook)
    data = service.read()
    data["rows"][0]["product_name"] = "Updated Product"
    result = service.write(data["rows"])

    updated = service.read()
    assert result["count"] == 1
    assert updated["rows"][0]["product_name"] == "Updated Product"
    assert Path(result["backup"]).name.startswith("partner_products_")
