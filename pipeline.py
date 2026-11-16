"""CSV validation, schema harmonisation, integration and preprocessing helpers."""
from __future__ import annotations

import json
import os
import re
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("EDUGUARD_DATA_DIR", BASE_DIR / "data"))
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_MIME_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream"}


class DatasetError(ValueError):
    pass


def validate_upload(filename: str, content_type: str, size_bytes: int | None = None) -> None:
    if Path(filename).suffix.lower() != ".csv":
        raise DatasetError("Only .csv files are accepted.")
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise DatasetError(f"Unsupported content type: {content_type}")
    if size_bytes is not None and size_bytes > MAX_UPLOAD_BYTES:
        raise DatasetError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")


def load_dataset(path: Path) -> pd.DataFrame:
    # pandas makes duplicate CSV headers unique (for example `age`, `age.1`).
    # Inspect the raw header first so malformed schemas are rejected explicitly.
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        try:
            header = next(csv.reader(stream))
        except StopIteration as exc:
            raise DatasetError("CSV is empty.") from exc
    raw_headers = [str(c).strip() for c in header]
    if len(set(raw_headers)) != len(raw_headers):
        raise DatasetError("Duplicate column names are not allowed.")
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        frame = pd.read_csv(path, encoding="latin-1", low_memory=False)
    if frame.empty or len(frame.columns) == 0:
        raise DatasetError("CSV has no data rows or columns.")
    normalized = [str(c).strip() for c in frame.columns]
    if any(not x for x in normalized):
        raise DatasetError("Column names cannot be blank.")
    if len(set(normalized)) != len(normalized):
        raise DatasetError("Duplicate column names are not allowed.")
    frame.columns = normalized
    return frame


def inspect_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    missing = frame.isna().sum()
    duplicate_rows = int(frame.duplicated().sum())
    repeated_columns = [str(c) for c in frame.columns[frame.columns.duplicated()].tolist()]
    return {
        "valid": bool(len(frame) > 0 and len(frame.columns) > 0 and not repeated_columns),
        "row_count": int(len(frame)), "column_count": int(len(frame.columns)),
        "duplicate_rows": duplicate_rows,
        "missing_cells": int(missing.sum()),
        "columns": [{"name": str(c), "dtype": str(frame[c].dtype), "missing": int(missing[c]),
                     "missing_percent": round(float(missing[c] * 100 / max(len(frame), 1)), 2),
                     "unique": int(frame[c].nunique(dropna=True))} for c in frame.columns],
        "warnings": ([f"{duplicate_rows} duplicate rows found."] if duplicate_rows else []) +
                    (["Missing values are present; fit imputers on training data only."] if int(missing.sum()) else []),
    }


def dataset_metadata(dataset_id: str, filename: str, source: str, path: Path, size: int,
                     frame: pd.DataFrame, validation: dict[str, Any]) -> dict[str, Any]:
    return {"id": dataset_id, "filename": filename, "source": source, "path": str(path.resolve()),
            "size_bytes": size, "uploaded_at": pd.Timestamp.utcnow().isoformat(),
            "rows": len(frame), "columns": len(frame.columns), "column_names": list(frame.columns),
            "statistics": frame.describe(include="all").fillna("").to_dict(), "validation": validation}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _resolve_column(columns: list[str], requested: str) -> str:
    found = [c for c in columns if _key(c) == _key(requested)]
    if len(found) != 1:
        raise DatasetError(f"Mapping column '{requested}' resolved to {len(found)} columns. Check source headers and feature_mapping.json.")
    return found[0]


def integrate_datasets(items: list[dict[str, Any]], mapping_path: Path,
                       target_mode: str = "preserve") -> dict[str, Any]:
    """Concatenate independently observed rows after applying declared feature mappings."""
    config = json.loads(mapping_path.read_text(encoding="utf-8"))
    ds_config = config.get("datasets", {})
    frames: list[pd.DataFrame] = []
    reports: list[dict[str, Any]] = []
    mappings: dict[str, Any] = {}
    for item in items:
        raw = load_dataset(Path(item["path"]))
        source_key = item["source"]
        source_cfg = ds_config.get(source_key)
        if not source_cfg:
            raise DatasetError(f"No mapping configured for source '{source_key}'. Set the upload source to a key in feature_mapping.json.")
        target_col = _resolve_column(list(raw.columns), source_cfg["target"])
        mapped: dict[str, pd.Series] = {}
        resolved: dict[str, str] = {}
        for common, source_column in source_cfg.get("features", {}).items():
            if source_column is None:
                continue
            if isinstance(source_column, dict):
                actuals = [_resolve_column(list(raw.columns), c) for c in source_column["columns"]]
                resolved[common] = " + ".join(actuals)
                mapped[common] = _derive_feature(raw, actuals, source_column)
            else:
                actual = _resolve_column(list(raw.columns), source_column)
                mapped[common] = raw[actual]
                resolved[common] = actual
        mapped["source"] = pd.Series([source_key] * len(raw), index=raw.index)
        label = raw[target_col].astype("string").str.strip()
        if target_mode == "binary_dropout":
            labels_cfg = source_cfg.get("binary_target", {})
            lookup = {_key(str(k)): v for k, v in labels_cfg.items()}
            mapped_vals = [lookup.get(_key(str(v))) if pd.notna(v) else None for v in label]
            mapped["target_binary_dropout"] = pd.Series(mapped_vals, index=raw.index, dtype="Int64")
            unknown = sorted(set(label.dropna().astype(str)) - set(str(k) for k in labels_cfg))
            # Case/space-insensitive matching is handled by the normalized lookup.
            if unknown and any(_key(v) not in lookup for v in unknown):
                raise DatasetError(f"Unmapped target label(s) in {source_key}: {unknown[:8]}")
        elif target_mode == "preserve":
            mapped["target_original"] = label
        else:
            raise DatasetError("target_mode must be 'preserve' or 'binary_dropout'.")
        frames.append(pd.DataFrame(mapped))
        reports.append({"source": source_key, "rows": len(raw), "columns": len(raw.columns),
                        "target_column": target_col, "missing_values": int(raw.isna().sum().sum()),
                        "duplicate_rows": int(raw.duplicated().sum())})
        mappings[source_key] = {"features": resolved, "target": target_col}
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = add_missingness_flags(combined)
    target_column = "target_binary_dropout" if target_mode == "binary_dropout" else "target_original"
    target_counts = {("null" if pd.isna(k) or k is pd.NA else str(k)): int(v)
                     for k, v in combined[target_column].value_counts(dropna=False).items()}
    return {"data": combined, "mapping": mappings, "statistics": {"sources": reports,
            "combined_rows": len(combined), "combined_columns": len(combined.columns),
            "missing_by_column": combined.isna().sum().astype(int).to_dict(),
            "target_column": target_column,
            "target_counts": target_counts}}


def add_missingness_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Add provenance-aware absent-feature indicators before any imputation."""
    out = frame.copy()
    source = out.get("source")
    for column in list(out.columns):
        if column in {"source", "target_original", "target_binary_dropout"}:
            continue
        if source is not None and out[column].isna().any():
            out[f"{column}__missing"] = out[column].isna().astype("int8")
    return out


def _derive_feature(raw: pd.DataFrame, columns: list[str], spec: dict[str, Any]) -> pd.Series:
    """Small allowlisted feature-expression set; no arbitrary code is evaluated."""
    operation = spec["operation"]
    values = [pd.to_numeric(raw[c], errors="coerce") for c in columns]
    if operation == "max":
        return pd.concat(values, axis=1).max(axis=1)
    if operation == "sum":
        return pd.concat(values, axis=1).sum(axis=1, min_count=1)
    if operation == "mean":
        return pd.concat(values, axis=1).mean(axis=1)
    if operation == "first":
        return values[0]
    if operation == "difference":
        return values[0] - values[1]
    if operation == "ratio":
        return values[0].div(values[1].replace(0, np.nan))
    if operation == "percentile_mean":
        ranks = [raw[c].rank(pct=True, method="average") for c in columns]
        return pd.concat(ranks, axis=1).mean(axis=1)
    if operation == "single_percentile":
        return raw[columns[0]].rank(pct=True, method="average")
    if operation == "percentile_difference":
        return raw[columns[0]].rank(pct=True, method="average") - raw[columns[1]].rank(pct=True, method="average")
    if operation == "one_minus_ratio":
        return 1 - values[0].div(values[1].replace(0, np.nan))
    if operation == "financial_stress":
        debtor = pd.to_numeric(raw[columns[0]], errors="coerce").eq(1)
        fees_late = pd.to_numeric(raw[columns[1]], errors="coerce").eq(0)
        return (debtor | fees_late).astype("int8")
    raise DatasetError(f"Unsupported feature operation: {operation}")


def build_preprocessor():
    """Return a sklearn transformer; call fit only on training folds to prevent leakage."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True))])
    return ColumnTransformer([("numeric", numeric, make_column_selector("number")),
                              ("categorical", categorical, make_column_selector("object", "category", "string"))],
                             remainder="drop")


def make_column_selector(*dtypes: str):
    from sklearn.compose import make_column_selector as selector
    return selector(dtype_include=list(dtypes))
