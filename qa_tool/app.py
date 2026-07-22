"""FastAPI application for the Intel Edge AI QA Automation Tool."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from qa_tool.services import (
    RUNS_DIR,
    RunManager,
    TestDataService,
    environment_summary,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Intel Edge AI QA Automation Tool",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

run_manager = RunManager()
test_data_service = TestDataService()


class RunRequest(BaseModel):
    environment: str = Field(default="qa", pattern="^(demo|qa|live)$")
    suite: str = Field(
        default="smoke", pattern="^(full|smoke|regression|catalog|partner)$"
    )
    browser: str = Field(default="chromium", pattern="^(chromium|firefox|webkit)$")
    headed: bool = False
    slow_mo: int = Field(default=500, ge=0, le=5000)
    test_id: str = Field(default="", max_length=80)


class TestDataPayload(BaseModel):
    rows: list[dict[str, Any]]


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "qa-automation-tool"}


@app.get("/api/summary")
def summary():
    data = test_data_service.read()
    runs = run_manager.list_runs()
    active = run_manager.active_run()
    return {
        "products": data["count"],
        "enabled_products": data["enabled_count"],
        "total_runs": len(runs),
        "passed_runs": sum(run["status"] == "passed" for run in runs),
        "failed_runs": sum(
            run["status"] in ("failed", "error") for run in runs
        ),
        "active_run": active,
        "recent_runs": runs[:5],
    }


@app.get("/api/environments")
def environments():
    return {"environments": environment_summary()}


@app.get("/api/test-data")
def get_test_data():
    return test_data_service.read()


@app.put("/api/test-data")
def save_test_data(payload: TestDataPayload):
    try:
        return test_data_service.write(
            payload.rows, run_active=run_manager.active_run() is not None
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=409,
            detail="Close partner_products.xlsx in Excel and try again.",
        ) from exc


@app.get("/api/runs")
def list_runs():
    return {"runs": run_manager.list_runs(), "active": run_manager.active_run()}


@app.post("/api/runs", status_code=202)
def start_run(request: RunRequest):
    try:
        return run_manager.start(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = run_manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    run["artifacts"] = run_manager.artifacts(run_id)
    return run


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    try:
        return run_manager.cancel(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found.") from exc


@app.get("/api/runs/{run_id}/log")
def run_log(run_id: str, offset: int = Query(default=0, ge=0)):
    if not run_manager.get(run_id):
        raise HTTPException(status_code=404, detail="Run not found.")
    return run_manager.log(run_id, offset)


@app.get("/api/runs/{run_id}/artifacts")
def list_artifacts(run_id: str):
    if not run_manager.get(run_id):
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"artifacts": run_manager.artifacts(run_id)}


@app.get("/api/runs/{run_id}/artifacts/{relative:path}")
def download_artifact(run_id: str, relative: str, download: bool = False):
    try:
        path = run_manager.artifact_path(run_id, relative)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found.") from exc

    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    disposition = path.name if download else None
    return FileResponse(path, media_type=media_type, filename=disposition)


@app.get("/api/runtime")
def runtime_info():
    active = run_manager.active_run()
    return {
        "active": active,
        "run_storage": str(RUNS_DIR),
        "one_run_at_a_time": True,
        "api_docs": "/api/docs",
    }
