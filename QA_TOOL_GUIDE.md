# EdgeQA Automation Console

EdgeQA is a local web application for running and managing the existing
Playwright/Pytest framework. It does not expose arbitrary shell commands and
binds to `127.0.0.1` by default.

## Start the tool

Double-click:

```text
launch_qa_tool.bat
```

Or run:

```powershell
.\venv\Scripts\python.exe launch_qa_tool.py
```

The browser opens at `http://127.0.0.1:8765`. Press `Ctrl+C` in the launcher
terminal to stop it.

## Dashboard features

- Launch Smoke, Regression, Catalog, Partner Spotlight, or Full test suites.
- Select Demo, QA, or Live and Chromium, Firefox, or WebKit.
- Run headless or show the browser with configurable slow motion.
- Filter a run to one test ID, such as `PS-005`.
- Watch live pytest/Playwright console output and cancel an active run.
- Review persistent run history and download HTML, Excel, Allure, and log files.
- Enable, disable, add, edit, and delete Excel-driven product test data.
- View all configured environment URLs and configuration warnings.

## Environment mapping

- **Demo** uses `config/environments/dev.json`
- **QA** uses `config/environments/staging.json`
- **Live** uses `config/environments/prod.json`

Update these JSON files with the actual server URLs for your organization.
The dashboard warns when QA and Live point to the same base URL. Live must be
explicitly selected in the launch form.

## Safety and data handling

- One automation run is allowed at a time because the existing framework uses
  shared report and screenshot directories.
- Test options are allowlisted; the API cannot execute custom commands.
- Excel saves require unique `test_id` values and required partner/product
  fields.
- Before every Excel save, a timestamped backup is created in
  `testdata/backups/`.
- Excel writes use a temporary verified workbook followed by atomic replacement.
- Excel cannot be edited through the dashboard while a test is running.
- Dashboard run metadata and copied artifacts are stored under `qa_tool/data/`
  and are excluded from Git.

## API

Interactive API documentation is available at:

```text
http://127.0.0.1:8765/api/docs
```

Important endpoints:

- `POST /api/runs` — start an allowlisted test run
- `GET /api/runs` — run history and current active run
- `GET /api/runs/{id}/log` — incremental console output
- `GET /api/runs/{id}/artifacts` — downloadable run artifacts
- `GET /api/test-data` — Excel rows and columns
- `PUT /api/test-data` — validated atomic Excel save
- `GET /api/environments` — Demo/QA/Live configuration

## First-time setup

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

Install Firefox or WebKit separately before selecting them:

```powershell
.\venv\Scripts\python.exe -m playwright install firefox webkit
```
