"""Data access and analytics for the Student Dropout Early Warning project.

The service reads the existing Member 3/Member 2 CSV outputs. Clustering and
PCA use only the declared student features; outcomes and provenance are kept
for interpreting results, never used to fit the unsupervised models.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.environ.get("MEMBER4_DATA_DIR", PROJECT_ROOT / "student_dropout_project_outputs"))
DATASET_FILE = "combined_student_dropout_dataset.csv"
PREDICTIONS_FILE = "student_risk_predictions.csv"
MODEL_METRICS_FILE = "model_comparison.csv"
CV_METRICS_FILE = "cross_validation_results.csv"
FEATURES = [
    "age", "gender", "scholarship", "academic_overall", "academic_recent",
    "academic_trend", "engagement_proxy",
]
CATEGORY_LABELS = {
    "gender": {"0": "Female", "0.0": "Female", "female": "Female", "1": "Male", "1.0": "Male", "male": "Male"},
    "scholarship": {"0": "No", "0.0": "No", "no": "No", "1": "Yes", "1.0": "Yes", "yes": "Yes"},
}
MAX_CLUSTER_ROWS = 3000
MAX_PLOT_ROWS = 650
RANDOM_STATE = 42


class AnalyticsDataError(RuntimeError):
    """Raised when a required project output is missing or malformed."""


def _category_label(column: str, value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    cleaned = str(value).strip()
    return CATEGORY_LABELS.get(column, {}).get(cleaned.casefold(), cleaned)


def _read_csv(filename: str, required: list[str] | None = None) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise AnalyticsDataError(f"Required project output not found: {path}")
    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as exc:  # pandas exposes several parser/encoding exceptions
        raise AnalyticsDataError(f"Could not read {filename}: {exc}") from exc
    missing = sorted(set(required or []) - set(frame.columns))
    if missing:
        raise AnalyticsDataError(f"{filename} is missing required column(s): {', '.join(missing)}")
    return frame


@lru_cache(maxsize=1)
def dataset() -> pd.DataFrame:
    return _read_csv(DATASET_FILE, FEATURES + ["target", "data_source"])


@lru_cache(maxsize=1)
def predictions() -> pd.DataFrame:
    return _read_csv(PREDICTIONS_FILE, FEATURES + ["dropout_probability", "risk_level"])


@lru_cache(maxsize=1)
def model_metrics() -> pd.DataFrame:
    return _read_csv(MODEL_METRICS_FILE, ["Model", "Accuracy", "Precision", "Recall", "F1 Score", "ROC AUC", "PR AUC", "MCC"])


@lru_cache(maxsize=1)
def cv_metrics() -> pd.DataFrame:
    path = OUTPUT_DIR / CV_METRICS_FILE
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).items()}


def summary() -> dict[str, Any]:
    frame = dataset()
    risk = predictions()
    target = pd.to_numeric(frame["target"], errors="coerce")
    metrics = model_metrics().sort_values("ROC AUC", ascending=False)
    missing = frame.isna().sum()
    duplicate_rows = int(frame.duplicated().sum())
    return {
        "record_count": int(len(frame)),
        "feature_count": int(len(FEATURES)),
        "features": FEATURES,
        "dropout_count": int(target.eq(1).sum()),
        "retained_count": int(target.eq(0).sum()),
        "dropout_rate": round(float(target.mean() * 100), 2),
        "class_distribution": _counts(target.map({0: "Retained", 1: "Dropout"}).fillna("Unknown")),
        "source_distribution": _counts(frame["data_source"].fillna("Unknown")),
        "risk_distribution": _counts(risk["risk_level"].fillna("Unknown")),
        "missing_values": {str(k): int(v) for k, v in missing.items()},
        "missing_cells": int(missing.sum()),
        "duplicate_rows": duplicate_rows,
        "best_model_by_roc_auc": str(metrics.iloc[0]["Model"]) if not metrics.empty else None,
        "best_roc_auc": round(float(metrics.iloc[0]["ROC AUC"]), 4) if not metrics.empty else None,
    }


def comparison() -> dict[str, Any]:
    frame = model_metrics().copy()
    cv = cv_metrics()
    rows = frame.replace({np.nan: None}).to_dict(orient="records")
    cv_rows = cv.replace({np.nan: None}).to_dict(orient="records") if not cv.empty else []
    return {"metrics": rows, "cross_validation": cv_rows, "metric_names": ["Accuracy", "Precision", "Recall", "F1 Score", "ROC AUC", "PR AUC", "MCC"]}


def quality() -> dict[str, Any]:
    frame = dataset()
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [
            {"name": str(column), "dtype": str(frame[column].dtype),
             "missing": int(frame[column].isna().sum()),
             "missing_percent": round(float(frame[column].isna().mean() * 100), 2),
             "unique": int(frame[column].nunique(dropna=True))}
            for column in frame.columns
        ],
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_cells": int(frame.isna().sum().sum()),
    }


def _sample() -> pd.DataFrame:
    frame = dataset()
    return frame.sample(n=min(len(frame), MAX_CLUSTER_ROWS), random_state=RANDOM_STATE).reset_index(drop=True)


def _feature_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Impute and one-hot encode features without using labels or source."""
    raw = frame[FEATURES].copy()
    categorical = [name for name in ("gender", "scholarship") if name in raw]
    for name in categorical:
        raw[name] = raw[name].map(lambda value: _category_label(name, value)).astype("string").fillna("Missing").astype(str)
    numeric = [name for name in FEATURES if name not in categorical]
    for name in numeric:
        raw[name] = pd.to_numeric(raw[name], errors="coerce")
    if numeric:
        raw[numeric] = SimpleImputer(strategy="median").fit_transform(raw[numeric])
    encoded = pd.get_dummies(raw, columns=categorical, dtype=float)
    values = encoded.to_numpy(dtype=float)
    values = StandardScaler().fit_transform(values)
    return values, [str(column) for column in encoded.columns]


@lru_cache(maxsize=1)
def cluster_results() -> dict[str, Any]:
    frame = _sample()
    matrix, _ = _feature_matrix(frame)
    if len(frame) < 3:
        raise AnalyticsDataError("At least three usable records are required for clustering.")
    candidate_counts = list(range(2, min(7, len(frame))))
    count_diagnostics = []
    for candidate_k in candidate_counts:
        candidate = KMeans(n_clusters=candidate_k, random_state=RANDOM_STATE, n_init=5)
        candidate_labels = candidate.fit_predict(matrix)
        count_diagnostics.append({
            "clusters": candidate_k,
            "inertia": round(float(candidate.inertia_), 3),
            "silhouette": round(float(silhouette_score(matrix, candidate_labels, sample_size=min(1000, len(candidate_labels)), random_state=RANDOM_STATE)), 4),
            "davies_bouldin": round(float(davies_bouldin_score(matrix, candidate_labels)), 4),
        })
    selected_k = max(count_diagnostics, key=lambda item: item["silhouette"])["clusters"]
    algorithms = {
        "K-Means": KMeans(n_clusters=selected_k, random_state=RANDOM_STATE, n_init=10),
        "Ward hierarchical": AgglomerativeClustering(n_clusters=selected_k, linkage="ward"),
        "Gaussian mixture": GaussianMixture(n_components=selected_k, random_state=RANDOM_STATE, n_init=3),
    }
    outcomes = pd.to_numeric(frame["target"], errors="coerce")
    results: dict[str, Any] = {
        "sample_size": int(len(frame)), "dataset_size": int(len(dataset())),
        "selected_cluster_count": int(selected_k), "cluster_count_diagnostics": count_diagnostics,
        "selection_method": "Highest sampled silhouette among K-Means candidates; inertia and Davies-Bouldin are reported for review.",
        "algorithms": {},
    }
    for name, estimator in algorithms.items():
        labels = estimator.fit_predict(matrix)
        diagnostics = {
            "silhouette": round(float(silhouette_score(matrix, labels, sample_size=min(1000, len(labels)), random_state=RANDOM_STATE)), 4),
            "davies_bouldin": round(float(davies_bouldin_score(matrix, labels)), 4),
            "adjusted_rand_vs_target": round(float(adjusted_rand_score(outcomes.fillna(0).astype(int), labels)), 4),
        }
        clusters = []
        for label in sorted(np.unique(labels)):
            selected = labels == label
            rows = frame.loc[selected]
            dropouts = pd.to_numeric(rows["target"], errors="coerce")
            clusters.append({
                "cluster": int(label),
                "records": int(selected.sum()),
                "dropout_rate": round(float(dropouts.mean() * 100), 2),
                "mean_academic_overall": round(float(pd.to_numeric(rows["academic_overall"], errors="coerce").mean()), 3),
                "mean_engagement": round(float(pd.to_numeric(rows["engagement_proxy"], errors="coerce").mean()), 3),
                "sources": _counts(rows["data_source"].fillna("Unknown")),
            })
        results["algorithms"][name] = {"diagnostics": diagnostics, "clusters": clusters}
    return results


@lru_cache(maxsize=1)
def pca_result() -> dict[str, Any]:
    frame = _sample()
    matrix, _ = _feature_matrix(frame)
    if matrix.shape[0] < 2 or matrix.shape[1] < 2:
        raise AnalyticsDataError("At least two rows and two encoded features are required for PCA.")
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    scores = pca.fit_transform(matrix)
    points = pd.DataFrame({
        "pc1": scores[:, 0], "pc2": scores[:, 1],
        "target": pd.to_numeric(frame["target"], errors="coerce").fillna(0).astype(int),
        "source": frame["data_source"].fillna("Unknown").astype(str),
    })
    if len(points) > MAX_PLOT_ROWS:
        points = points.sample(n=MAX_PLOT_ROWS, random_state=RANDOM_STATE)
    return {
        "sample_size": int(len(frame)),
        "plot_size": int(len(points)),
        "explained_variance_ratio": [round(float(v), 4) for v in pca.explained_variance_ratio_],
        "points": points.round(4).to_dict(orient="records"),
    }


def feature_importance() -> dict[str, Any]:
    """Prefer saved tree-model importances; fall back to labeled MI association."""
    import joblib

    from sklearn.feature_selection import mutual_info_classif

    frame = dataset()
    candidate_files = ["xgboost.joblib", "lightgbm.joblib"]
    load_notes: list[str] = []
    for filename in candidate_files:
        path = OUTPUT_DIR / filename
        if not path.is_file():
            continue
        try:
            model = joblib.load(path)
            values = getattr(model, "feature_importances_", None)
            if values is None and hasattr(model, "named_steps"):
                last = list(model.named_steps.values())[-1]
                values = getattr(last, "feature_importances_", None)
            if values is None:
                load_notes.append(f"{filename} loaded but exposes no tree feature_importances_.")
                continue
            raw_names = list(getattr(model, "feature_names_in_", []))
            if len(raw_names) != len(values):
                raw_names = [f"Feature {i + 1}" for i in range(len(values))]
            items = [{"feature": str(name), "importance": float(value)} for name, value in zip(raw_names, values)]
            items.sort(key=lambda item: item["importance"], reverse=True)
            return {"method": f"Saved model: {filename}", "interpretation": "Model-reported tree importance; association is not causation.", "items": items[:15], "note": None}
        except Exception as exc:
            load_notes.append(f"{filename} could not be loaded in this environment: {type(exc).__name__}.")

    matrix, names = _feature_matrix(frame)
    target = pd.to_numeric(frame["target"], errors="coerce").fillna(0).astype(int).to_numpy()
    sample_indices = np.arange(len(target))
    if len(target) > 5000:
        sample_indices = np.random.RandomState(RANDOM_STATE).choice(sample_indices, 5000, replace=False)
    scores = mutual_info_classif(matrix[sample_indices], target[sample_indices], random_state=RANDOM_STATE)
    items = [{"feature": name, "importance": float(score)} for name, score in zip(names, scores)]
    items.sort(key=lambda item: item["importance"], reverse=True)
    note = "Showing univariate mutual-information association with the recorded target, not model-derived importance. " + " ".join(load_notes)
    return {"method": "Mutual information (exploratory fallback)", "interpretation": "Association only; not causal and not an explanation of a specific model prediction.", "items": items[:15], "note": note}


def risk_records(limit: int = 100) -> dict[str, Any]:
    frame = predictions().copy()
    limit = max(1, min(int(limit), 500))
    frame.insert(0, "record_id", np.arange(len(frame), dtype=int))
    for column in ("gender", "scholarship"):
        if column in frame:
            frame[column] = frame[column].map(lambda value: _category_label(column, value))
    frame["dropout_probability"] = pd.to_numeric(frame["dropout_probability"], errors="coerce").round(4)
    return {"total": int(len(frame)), "records": frame.head(limit).replace({np.nan: None}).to_dict(orient="records")}


def explain_prediction(record_id: int, model_name: str = "xgboost") -> dict[str, Any]:
    """Return SHAP values only when the saved model and SHAP runtime are usable."""
    frame = predictions()
    if record_id < 0 or record_id >= len(frame):
        raise IndexError(f"Prediction record must be between 0 and {len(frame) - 1}.")
    filename = {"xgboost": "xgboost.joblib", "lightgbm": "lightgbm.joblib"}.get(model_name.lower())
    if filename is None:
        raise ValueError("Choose either xgboost or lightgbm.")
    path = OUTPUT_DIR / filename
    record = frame.iloc[record_id]
    base = {
        "record_id": int(record_id), "model": model_name,
        "dropout_probability": float(record["dropout_probability"]),
        "risk_level": str(record["risk_level"]),
        "student_features": {
            name: (None if pd.isna(record[name]) else _category_label(name, record[name]) if name in CATEGORY_LABELS else record[name].item() if hasattr(record[name], "item") else record[name])
            for name in FEATURES
        },
    }
    if not path.is_file():
        return {**base, "available": False, "method": None, "values": [], "message": f"Saved {model_name} artifact was not found."}
    try:
        import joblib
        import shap

        model = joblib.load(path)
        row = pd.DataFrame([{name: record[name] for name in FEATURES}])
        explainer = shap.TreeExplainer(model)
        explanation = explainer(row)
        values = np.asarray(explanation.values)
        if values.ndim == 3:
            values = values[0, :, -1]
        elif values.ndim == 2:
            values = values[0]
        values = np.asarray(values).reshape(-1)
        names = list(getattr(explanation, "feature_names", None) or FEATURES)
        if len(names) != len(values):
            names = [f"Feature {i + 1}" for i in range(len(values))]
        items = [{"feature": str(name), "shap_value": float(value), "direction": "increases" if value > 0 else "decreases"} for name, value in zip(names, values)]
        items.sort(key=lambda item: abs(item["shap_value"]), reverse=True)
        return {**base, "available": True, "method": "SHAP TreeExplainer", "values": items, "message": "Positive and negative values show contribution direction in the model's output scale."}
    except Exception as exc:
        return {**base, "available": False, "method": None, "values": [], "message": f"SHAP explanation could not be produced in this environment ({type(exc).__name__}). Check the model artifact/runtime compatibility and SHAP installation."}


def report_data() -> dict[str, Any]:
    return {
        "title": "Student Dropout Analytics Summary",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "summary": summary(),
        "model_comparison": comparison(),
        "data_quality": quality(),
        "clustering": cluster_results(),
    }


def serialize_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)

