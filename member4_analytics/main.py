"""Standalone FastAPI app for Member 4 analytics and reporting."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import analytics_service as service


BASE_DIR = Path(__file__).resolve().parent
router = APIRouter()
app = FastAPI(
    title="Student Dropout Analytics API",
    description="Member 4 analytics, unsupervised learning, explainability and report endpoints.",
    version="1.0.0",
)
app.mount("/member4/static", StaticFiles(directory=BASE_DIR / "static"), name="member4-static")


@router.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> HTMLResponse:
    content = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=content, headers={"Cache-Control": "no-store"})


@router.get("/api/analytics/health")
def health() -> dict[str, str]:
    return {"status": "ok", "module": "member4_analytics"}


@router.get("/api/analytics/summary")
def analytics_summary() -> dict:
    try:
        return service.summary()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/analytics/quality")
def analytics_quality() -> dict:
    try:
        return service.quality()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/analytics/model-comparison")
def analytics_model_comparison() -> dict:
    try:
        return service.comparison()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/analytics/clusters")
def analytics_clusters() -> dict:
    try:
        return service.cluster_results()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {type(exc).__name__}: {exc}") from exc


@router.get("/api/analytics/pca")
def analytics_pca() -> dict:
    try:
        return service.pca_result()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PCA failed: {type(exc).__name__}: {exc}") from exc


@router.get("/api/analytics/feature-importance")
def analytics_feature_importance() -> dict:
    try:
        return service.feature_importance()
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feature importance failed: {type(exc).__name__}: {exc}") from exc


@router.get("/api/analytics/predictions")
def analytics_predictions(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    try:
        return service.risk_records(limit)
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/analytics/explain/{record_id}")
def analytics_explain(record_id: int, model: str = Query(default="xgboost")) -> dict:
    try:
        return service.explain_prediction(record_id, model)
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/analytics/report")
def analytics_report(format: str = Query(default="json", pattern="^(json|csv)$")) -> Response:
    try:
        report = service.report_data()
        if format == "json":
            return Response(service.serialize_json(report), media_type="application/json", headers={"Content-Disposition": "attachment; filename=student_dropout_analytics_report.json"})
        rows = []
        rows.append({"section": "dataset", "name": "record_count", "value": report["summary"]["record_count"]})
        rows.append({"section": "dataset", "name": "dropout_rate_percent", "value": report["summary"]["dropout_rate"]})
        rows.append({"section": "dataset", "name": "duplicate_rows", "value": report["data_quality"]["duplicate_rows"]})
        for entry in report["model_comparison"]["metrics"]:
            for key, value in entry.items():
                if key != "Model":
                    rows.append({"section": "model_comparison", "name": f"{entry['Model']} - {key}", "value": value})
        for candidate in report["clustering"]["cluster_count_diagnostics"]:
            for metric_name in ("inertia", "silhouette", "davies_bouldin"):
                rows.append({"section": "cluster_count_selection", "name": f"k_{candidate['clusters']}_{metric_name}", "value": candidate[metric_name]})
        for algorithm, result in report["clustering"]["algorithms"].items():
            for metric_name, metric_value in result["diagnostics"].items():
                rows.append({"section": algorithm, "name": metric_name, "value": metric_value})
            for cluster in result["clusters"]:
                rows.append({"section": algorithm, "name": f"cluster_{cluster['cluster']}_dropout_rate_percent", "value": cluster["dropout_rate"]})
        content = pd.DataFrame(rows).to_csv(index=False)
        return Response(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=student_dropout_analytics_report.csv"})
    except service.AnalyticsDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {type(exc).__name__}: {exc}") from exc


app.include_router(router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def standalone_dashboard() -> HTMLResponse:
    return dashboard()

