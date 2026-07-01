# Intel Edge AI Automation Framework

Production-grade Playwright + Pytest automation framework using Page Object Model, Excel-driven data, Allure/HTML reporting, parallel execution, and environment-based configuration.

## Features

| Capability | Implementation |
|---|---|
| Page Object Model | `pages/base_page.py` + feature pages |
| Excel-driven tests | `utilities/excel_reader.py` + `testdata/partner_products.xlsx` |
| HTML reporting | `pytest-html` via `pytest.ini` |
| Allure reporting | `allure-pytest` via `pytest.ini` |
| Screenshot on failure | `conftest.py` + `utilities/screenshot_util.py` |
| Logging | `utilities/logger.py` (console + file) |
| PDF validation | `utilities/pdf_validator.py` |
| Resource link validation | `utilities/link_validator.py` |
| Partner logo validation | `utilities/logo_validator.py` |
| Product detail validation | `pages/product_detail_page.py` |
| Category/subcategory | `pages/edge_catalog_page.py` |
| Grid/List view | `pages/base_page.py` |
| Search | `pages/base_page.py` |
| Breadcrumb validation | `utilities/breadcrumb_validator.py` |
| Metadata validation | `utilities/metadata_validator.py` |
| Parallel execution | `pytest-xdist` (`-n auto`) |
| Retry failed tests | `pytest-rerunfailures` (`--reruns 2`) |
| Environment config | `config/environments/*.json` + `TEST_ENV` |

## Project Structure

```
intel_edge_ai_automation/
├── config/
│   ├── config.json
│   └── environments/
│       ├── dev.json
│       ├── staging.json
│       └── prod.json
├── pages/
│   ├── base_page.py
│   ├── home_page.py
│   ├── edge_catalog_page.py
│   ├── partner_spotlight_page.py
│   └── product_detail_page.py
├── tests/
│   ├── test_partner_spotlight.py
│   ├── test_catalog_features.py
│   └── helpers.py
├── utilities/
│   ├── base validators, excel, logger, screenshot, constants
│   └── test_data_provider.py
├── testdata/
├── downloads/
├── screenshots/
├── reports/
├── conftest.py
├── pytest.ini
└── requirements.txt
```

## Setup

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m playwright install chromium
```

### Windows PowerShell note

If `Activate.ps1` fails with *running scripts is disabled*, you do **not** need to activate the venv. Use the venv Python directly:

```powershell
# Run tests (no activation required)
.\venv\Scripts\python.exe -m pytest

# Or use the batch helper
.\run_tests.bat -m smoke -v
```

To enable `Activate.ps1` permanently for your user only (optional):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

> **Do not run `conftest.py` directly** — it is pytest configuration, not a test runner. Use `pytest` or `python -m pytest` instead.

## Configuration

**Global settings:** `config/config.json`  
**Environment URLs:** `config/environments/{dev|staging|prod}.json`

```bash
# Run against staging
set TEST_ENV=staging
pytest

# Or via CLI flag
pytest --env=dev --headed
```

## Excel Test Data (`testdata/partner_products.xlsx`)

| Column | Description |
|---|---|
| `enabled` | `true` / `false` — include row in tests |
| `test_id` | Unique test identifier |
| `partner_name` | Partner to select |
| `product_name` | Product to open |
| `category` | Optional category filter |
| `subcategory` | Optional subcategory filter |
| `search_term` | Optional search term |
| `expected_title` | Expected product title |
| `expected_description` | Expected description snippet |
| `expected_breadcrumb` | e.g. `Home > Catalog > Product` |
| `expected_meta_description` | Meta description check |
| `validate_logo` | `true` / `false` |
| `validate_grid_view` | `true` / `false` |
| `validate_list_view` | `true` / `false` |
| `validate_breadcrumb` | `true` / `false` |
| `validate_metadata` | `true` / `false` |
| `validate_resources` | `true` / `false` |
| `validate_pdf` | `true` / `false` |
| `expected_pdf_text` | Text to find in downloaded PDF |

## Run Tests

```bash
# Full regression
pytest

# Smoke only
pytest -m smoke

# Partner tests only
pytest -m partner

# Parallel (4 workers)
pytest -n 4

# Parallel auto-detect CPU cores
pytest -n auto

# Staging + headed browser
pytest --env=staging --headed

# Override retries
pytest --reruns 3 --reruns-delay 5
```

## Reports

- **HTML:** `reports/report.html`
- **Allure:** `reports/allure-results/` → `allure serve reports/allure-results`
- **Logs:** `reports/test_run_*.log`
- **Screenshots:** `screenshots/` (on failure)
