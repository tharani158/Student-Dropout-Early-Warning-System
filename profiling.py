"""Read-only, JSON-safe exploratory profiles for uploaded student CSV files."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd


TARGET_NAMES = ("Target", "target_original", "target_binary_dropout", "Status", "Outcome", "Dropout")
CODED_CATEGORICAL = {
    "Marital status", "Application mode", "Course", "Daytime/evening attendance",
    "Previous qualification", "Nacionality", "Mother's qualification",
    "Father's qualification", "Mother's occupation", "Father's occupation",
    "Displaced", "Educational special needs", "Debtor", "Tuition fees up to date",
    "Gender", "Scholarship holder", "International",
}
IDENTIFIERS = {"Student_ID"}


def _number(value: Any) -> float | None:
    value = float(value)
    return round(value, 4) if math.isfinite(value) else None


def detect_target(frame: pd.DataFrame) -> str | None:
    lookup = {re.sub(r"[^a-z0-9]", "", str(c).lower()): str(c) for c in frame.columns}
    for candidate in TARGET_NAMES:
        found = lookup.get(re.sub(r"[^a-z0-9]", "", candidate.lower()))
        if found:
            return found
    return None


def profile_dataframe(frame: pd.DataFrame, target: str | None = None) -> dict[str, Any]:
    """Profile every column; numeric outliers use the 1.5×IQR rule."""
    if target is None:
        target = detect_target(frame)
    if target is not None and target not in frame.columns:
        raise ValueError(f"Target column '{target}' does not exist.")
    rows = len(frame)
    columns = []
    outliers = []
    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        numeric = (pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
                   and name not in CODED_CATEGORICAL and name not in IDENTIFIERS and name != target)
        kind = "identifier" if name in IDENTIFIERS else ("numeric" if numeric else "categorical")
        counts = series.astype("string").fillna("(missing)").value_counts().head(10)
        item: dict[str, Any] = {
            "name": str(name), "dtype": str(series.dtype), "type": kind,
            "missing": missing, "missing_percent": round(100 * missing / rows, 2) if rows else 0,
            "unique": int(series.nunique(dropna=True)),
            "top_values": [{"value": str(k), "count": int(v)} for k, v in counts.items()],
        }
        if numeric:
            clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if len(clean):
                q1, median, q3 = clean.quantile([.25, .5, .75]).tolist()
                iqr = q3 - q1
                count = int(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).sum()) if iqr > 0 else 0
                item["summary"] = {"min": _number(clean.min()), "q1": _number(q1),
                                   "median": _number(median), "q3": _number(q3),
                                   "max": _number(clean.max()), "mean": _number(clean.mean())}
                item["outlier_count"] = count
                if count:
                    outliers.append({"feature": str(name), "count": count})
        columns.append(item)
    numeric_names = [x["name"] for x in columns if x["type"] == "numeric"]
    numeric_frame = frame[numeric_names].replace([np.inf, -np.inf], np.nan)
    # Coded categories, identifiers and the numeric target are deliberately excluded.
    corr = numeric_frame.corr(numeric_only=True).round(3)
    correlations = []
    for i, left in enumerate(corr.columns):
        for right in corr.columns[i + 1:]:
            value = corr.loc[left, right]
            if pd.notna(value):
                correlations.append({"feature_a": str(left), "feature_b": str(right), "pearson_r": float(value)})
    correlations.sort(key=lambda x: abs(x["pearson_r"]), reverse=True)
    duplicate_rows = int(frame.duplicated().sum())
    missing_cells = int(frame.isna().sum().sum())
    distribution = []
    if target:
        counts = frame[target].astype("string").fillna("(missing)").value_counts()
        distribution = [{"label": str(k), "count": int(v), "percent": round(100 * v / rows, 2)}
                        for k, v in counts.items()]
    issues = []
    if missing_cells:
        issues.append(f"{missing_cells} missing cells need review before model training.")
    if duplicate_rows:
        issues.append(f"{duplicate_rows} exact duplicate rows need investigation.")
    if target and frame[target].isna().any():
        issues.append("Some outcome labels are missing; exclude those rows from supervised training.")
    if target and distribution and max(x["count"] for x in distribution) / rows > .8:
        issues.append("The largest target class exceeds 80%; use class-aware evaluation.")
    if outliers:
        issues.append("Numeric outliers were flagged by the IQR rule; inspect them before removal.")
    return {"row_count": rows, "feature_count": len(frame.columns) - int(target is not None),
            "column_count": len(frame.columns), "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows, "target_column": target,
            "class_distribution": distribution, "columns": columns,
            "outliers": outliers, "correlations": correlations[:30], "quality_issues": issues}
