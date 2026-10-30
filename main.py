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

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
META_FILE = DATA_DIR / "metadata.json"

app = FastAPI(title="EduGuard Dataset Management API", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def read_metadata() -> dict[str, Any]:
    if not META_FILE.exists():
        return {"datasets": []}
    return json.loads(META_FILE.read_text(encoding="utf-8"))


def write_metadata(payload: dict[str, Any]) -> None:
    META_FILE.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/datasets")
def list_datasets() -> dict[str, Any]:
    payload = read_metadata()
    return {"datasets": [{k: v for k, v in item.items() if k != "path"} for item in payload["datasets"]]}


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
        write_metadata(state)
        return metadata
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
