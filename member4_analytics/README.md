# Member 4 Analytics Module

This standalone module adds the analytics, clustering, PCA, explainability, and reporting work to the existing `ML Project` folder. It reads the CSV and model artifacts in `../student_dropout_project_outputs/` and does not rewrite them.

## Run the dashboard

From the repository folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MEMBER4_DATA_DIR = (Resolve-Path ..\student_dropout_project_outputs).Path
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/analytics`. The existing dataset-management page remains at `/`. API documentation is at `http://127.0.0.1:8000/docs`.

Set `MEMBER4_DATA_DIR` to the folder containing the expected output CSVs before starting the server. The example above points to the adjacent `student_dropout_project_outputs` folder used during local development. When running elsewhere, copy the required output CSVs to a data folder and set the variable to that path.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/analytics/health` | Service status |
| GET | `/api/analytics/summary` | Record counts, dropout rate, source/risk/class distributions, and quality counts |
| GET | `/api/analytics/quality` | Per-column missingness, data types, unique values, and duplicate rows |
| GET | `/api/analytics/model-comparison` | Saved holdout and cross-validation metrics |
| GET | `/api/analytics/clusters` | Cluster-count sweep plus K-Means, Ward hierarchical, and Gaussian mixture profiles with silhouette, Davies-Bouldin, and adjusted Rand diagnostics |
| GET | `/api/analytics/pca` | Two-component PCA coordinates and explained variance |
| GET | `/api/analytics/feature-importance` | Saved tree importance where compatible; otherwise exploratory mutual information |
| GET | `/api/analytics/predictions?limit=100` | Risk records for the table and individual explanation selection |
| GET | `/api/analytics/explain/{record_id}?model=xgboost` | SHAP explanation when the artifact and optional dependencies support it |
| GET | `/api/analytics/report?format=json` | Download report as JSON (`csv` is also supported) |

## Analysis notes

- The dataset currently contains 13,630 combined rows from Kaggle and UCI source exports. The dashboard reads the supplied target and risk outputs as provided; it does not retrain the supervised models.
- Categorical values are normalized for display and unsupervised feature encoding: the UCI binary codes become `0 = Female`, `1 = Male`, `0 = No scholarship`, and `1 = Yes scholarship`, matching the dataset value definitions. The original CSV files remain unchanged.
- Clustering and PCA use the declared seven student features. `target`, `data_source`, and the pre-existing `cluster` column are excluded from the fit inputs. Source and target are attached only after clustering so cluster composition can be compared with recorded outcomes. Candidate cluster counts from 2 through 6 are scored with inertia, silhouette, and Davies-Bouldin; the highest-silhouette count is then shared across the three algorithms. Algorithm diagnostics also include adjusted Rand against the recorded target.
- Clustering uses a reproducible sample of at most 3,000 rows because Ward hierarchical clustering has quadratic memory/time behavior. PCA coordinates are sampled to at most 650 points for the dashboard.
- A cluster's observed dropout rate is descriptive. It is not a causal explanation or validated intervention threshold.
- XGBoost and LightGBM artifacts are attempted for feature importance and SHAP. If model deserialization or optional libraries fail, feature importance falls back to univariate mutual information and SHAP is reported as unavailable. The dashboard labels these methods clearly.
- Risk bands in the existing prediction CSV are displayed as already supplied. This module does not claim to derive validation-based thresholds because no threshold-selection artifact is present in this folder.
- The router is mounted into the team's existing FastAPI application. The analytics page is available at `/analytics`, with a link in the dataset-management navigation.

## Folder contents

- `analytics_service.py`: CSV loading, summaries, clustering, PCA, feature importance, explanations, and report serialization.
- `main.py`: FastAPI endpoints and static dashboard serving.
- `static/`: responsive dashboard for overview, model comparison, clusters, PCA, explanations, and report downloads.
