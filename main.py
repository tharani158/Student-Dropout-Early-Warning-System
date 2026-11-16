"""FastAPI application for the EduGuard dataset management module."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import (
    DATA_DIR, MAX_UPLOAD_BYTES, DatasetError, dataset_metadata, integrate_datasets,
    inspect_dataframe, load_dataset, validate_upload,
)
from member4_analytics.main import router as member4_analytics_router
from profiling import profile_dataframe
from feature_groups import feature_groups
from storage import read_state, write_state

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
META_FILE = DATA_DIR / "metadata.json"

app = FastAPI(title="EduGuard Dataset Management API", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/member4/static", StaticFiles(directory=BASE_DIR / "member4_analytics" / "static"), name="member4-static")
app.include_router(member4_analytics_router)


def read_metadata() -> dict[str, Any]:
    return read_state(META_FILE)


def write_metadata(payload: dict[str, Any]) -> None:
    write_state(META_FILE, payload)


def _public(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k != "path"}


def _activity(kind: str, description: str) -> None:
    state = read_metadata()
    state.setdefault("activities", []).insert(0, {"kind": kind, "description": description,
        "at": pd.Timestamp.now("UTC").isoformat()})
    state["activities"] = state["activities"][:50]
    write_metadata(state)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/datasets")
def list_datasets() -> dict[str, Any]:
    payload = read_metadata()
    return {"datasets": [_public(item) for item in payload["datasets"]]}


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    state = read_metadata()
    datasets = state["datasets"]
    distributions = {}
    for item in datasets:
        frame = load_dataset(Path(item["path"]))
        report = profile_dataframe(frame)
        distributions[item["id"]] = report["class_distribution"]
    return {"dataset_count": len(datasets), "total_records": sum(x["rows"] for x in datasets),
            "total_features": sum(x["columns"] for x in datasets),
            "missing_values": sum(x["validation"]["missing_cells"] for x in datasets),
            "datasets": [{"id": x["id"], "filename": x["filename"], "source": x["source"],
                          "rows": x["rows"], "columns": x["columns"], "uploaded_at": x["uploaded_at"],
                          "missing_values": x["validation"]["missing_cells"],
                          "duplicate_rows": x["validation"]["duplicate_rows"],
                          "class_distribution": distributions[x["id"]]} for x in datasets],
            "recent_activities": state.get("activities", [])[:10]}


@app.post("/api/activities/model")
def record_model_activity(body: dict[str, Any]) -> dict[str, Any]:
    """Let the model-training module report a completed run to the dashboard."""
    model = str(body.get("model", "")).strip()
    status = str(body.get("status", "")).strip()
    if not model or len(model) > 80 or status not in {"trained", "evaluated", "failed"}:
        raise HTTPException(status_code=422, detail="Provide a model name (1–80 chars) and status: trained, evaluated, or failed.")
    _activity("model", f"{model}: {status}")
    return {"status": "recorded"}


@app.get("/api/datasets/{dataset_id}/profile")
def dataset_profile(dataset_id: str, target: str | None = None) -> dict[str, Any]:
    item = _get_dataset(dataset_id)
    try:
        return profile_dataframe(load_dataset(Path(item["path"])), target)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/datasets/{dataset_id}/statistics")
def dataset_statistics(dataset_id: str) -> dict[str, Any]:
    return dataset_profile(dataset_id)


@app.get("/api/datasets/{dataset_id}/class-distribution")
def class_distribution(dataset_id: str, target: str | None = None) -> dict[str, Any]:
    profile = dataset_profile(dataset_id, target)
    return {"target_column": profile["target_column"], "classes": profile["class_distribution"]}


@app.get("/api/datasets/{dataset_id}/feature-groups")
def dataset_feature_groups(dataset_id: str) -> dict[str, Any]:
    item = _get_dataset(dataset_id)
    try:
        return feature_groups(load_dataset(Path(item["path"])), item["source"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), source: str = "unspecified") -> dict[str, Any]:
    try:
        validate_upload(file.filename or "", file.content_type or "")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        validate_upload(file.filename or "", file.content_type or "", size_bytes=len(data))
        dataset_id = uuid.uuid4().hex
        path = UPLOAD_DIR / f"{dataset_id}.csv"
        path.write_bytes(data)
        frame = load_dataset(path)
        result = inspect_dataframe(frame)
        metadata = dataset_metadata(dataset_id, file.filename or "dataset.csv", source, path, len(data), frame, result)
        state = read_metadata()
        state["datasets"].append(metadata)
        state.setdefault("activities", []).insert(0, {"kind": "upload", "description": f"Uploaded {metadata['filename']}", "at": metadata["uploaded_at"]})
        write_metadata(state)
        return _public(metadata)
    except DatasetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}") from exc


@app.get("/api/datasets/{dataset_id}/preview")
def preview_dataset(dataset_id: str, limit: int = 20) -> dict[str, Any]:
    item = _get_dataset(dataset_id)
    frame = load_dataset(Path(item["path"]))
    sample = frame.head(max(1, min(limit, 100))).astype(object)
    sample = sample.where(pd.notna(sample), None)
    return {"columns": list(frame.columns), "rows": sample.to_dict(orient="records")}


@app.get("/api/datasets/{dataset_id}/validation")
def validate_dataset(dataset_id: str) -> dict[str, Any]:
    return _get_dataset(dataset_id)["validation"]


@app.post("/api/integrate")
def integrate(body: dict[str, Any]) -> dict[str, Any]:
    ids = body.get("dataset_ids", [])
    mapping_path = body.get("mapping_path", "config/feature_mapping.json")
    target_mode = body.get("target_mode", "preserve")
    if len(ids) not in (1, 2) or (len(ids) == 2 and ids[0] == ids[1]):
        raise HTTPException(status_code=422, detail="Select one source for a standalone processed export or two distinct sources for integration.")
    items = [_get_dataset(x) for x in ids]
    try:
        result = integrate_datasets(items, BASE_DIR / mapping_path, target_mode)
        out = DATA_DIR / "processed" / f"integrated_{uuid.uuid4().hex[:8]}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        result["data"].to_csv(out, index=False)
        _activity("integration", f"Integrated {len(ids)} dataset(s) into {out.name}")
        return {"status": "complete", "download_url": f"/api/exports/{out.name}", "rows": len(result["data"]), "columns": list(result["data"].columns), "mapping": result["mapping"], "statistics": result["statistics"], "target_mode": target_mode}
    except (DatasetError, FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/exports/{filename}")
def export_dataset(filename: str) -> FileResponse:
    path = (DATA_DIR / "processed" / filename).resolve()
    if path.parent != (DATA_DIR / "processed").resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Export not found.")
    return FileResponse(path, media_type="text/csv", filename=filename)


def _get_dataset(dataset_id: str) -> dict[str, Any]:
    item = next((x for x in read_metadata()["datasets"] if x["id"] == dataset_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return item
