# EduGuard student dropout data workspace

Member 1 dashboard, profiling API, EDA notebook and report workflow: [docs/member1_eda_dashboard.md](docs/member1_eda_dashboard.md). The dashboard is the app's landing page; dataset upload and integration remain available in the sidebar.

The two cited datasets have been inspected. See [real-data findings](docs/eda_findings.md), [EDA notebooks](notebooks/), and [proposal-aligned feature groups](config/feature_groups.json). Downloaded CSVs and executed notebook outputs stay under `data/` and are excluded from Git. Run `.venv/bin/python scripts/run_eda.py` after downloading both files to regenerate report figures.

This module provides CSV upload and validation, metadata and preview APIs, source-aware schema harmonisation, row-wise concatenation, export, and a leakage-aware preprocessing entry point. The brief cites [Kaggle's Student dropout prediction dataset](https://www.kaggle.com/datasets/meharshanali/student-dropout-prediction-dataset) (10,000 synthetic records) and [UCI dataset 697](https://archive.ics.uci.edu/dataset/697/predict%2Bstudents%2Bdropout%2Band%2Bacademic%2Bsuccess) (4,424 Portuguese higher-education records, three classes). `download_datasets.py` downloads both and writes `data/raw/inspection_report.json` with observed columns and label counts. Kaggle access may require account consent/credentials.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. Uploaded files and metadata are stored under `data/`; integrated outputs are stored under `data/processed/`.

Download and inspect the cited datasets when credentials and network access are available:

```powershell
python download_datasets.py
```

The script saves both CSVs in `data/raw/` and a schema/quality report. If Kaggle access fails, download its CSV from the linked page and place it at `data/raw/kaggle_synthetic.csv`.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API status |
| GET | `/api/datasets` | Uploaded dataset metadata and validation summaries |
| POST | `/api/datasets/upload?source=kaggle_synthetic` | Upload CSV (`multipart/form-data`, field `file`); source may be `uci_portuguese` or `unspecified` |
| GET | `/api/datasets/{id}/preview?limit=20` | Preview up to 100 rows |
| GET | `/api/datasets/{id}/validation` | Validation result |
| POST | `/api/integrate` | Process one mapped source or integrate two mapped sources; JSON has `dataset_ids` and optional `target_mode` |
| GET | `/api/exports/{filename}` | Download integrated CSV |

Integration request example:

```json
{"dataset_ids":["first-upload-id","second-upload-id"],"target_mode":"preserve"}
```

`target_mode` is `preserve` by default and retains source labels as strings in `target_original`, including the UCI three-class outcome. Select a single UCI dataset to create a standalone three-class processed export; select two datasets for pooled row-wise integration. `binary_dropout` creates a separate binary target from explicitly configured label mappings; it does not replace the original target. The app never infers student identity or joins by row number.

## Dataset preparation and mapping

`config/feature_mapping.json` now uses headers observed in the downloaded Kaggle v3 and UCI files. It maps age, scholarship and within-source academic percentiles. Gender and parental-education codes are left unmapped because their meanings differ. A feature should only be mapped when its definition matches. The `source` field is provenance, not a student identifier.

The downloaded Kaggle file has 10,000 rows and a binary `Dropout` target (0/1). UCI has 4,424 rows and a three-class `Target`. See [measured EDA findings](docs/eda_findings.md). Recheck the mapping if either source file changes version.

Validation reports row and column counts, inferred dtypes, missingness, unique values, duplicate records, and warnings. Duplicate rows are reported but not silently removed. Invalid file type, blank/duplicate headers, empty files, unreadable CSVs, and uploads over 20 MB are rejected.

## Preprocessing without leakage

Integration does not impute or scale the full combined file. Run the training-preparation CLI after integration:

```powershell
python preprocessing.py data\processed\integrated_<id>.csv target_original --output data\experiments\uci_three_class
python preprocessing.py data\processed\integrated_<id>.csv target_binary_dropout --output data\experiments\binary_dropout
```

The first command is created by selecting only the UCI upload in the integration page and keeping `preserve` mode; replace `<id>` with the export filename. Do not use `target_original` on a mixed multi-source target if source label semantics differ. For supervised comparison, prepare each source separately, then use `target_binary_dropout` only for the documented binary experiment. The script stratifies where feasible, holds out 20% with a fixed seed, fits numeric median imputation, categorical mode imputation, one-hot encoding, and scaling on training rows only, and transforms the test rows with that fitted transformer. It excludes `source` from model features by default and saves it separately for source-specific metrics. Keep the test set untouched through model and threshold selection.

For source-balanced/transfer experiments, create splits stratified by both source and target, then run source-only train/test transfers. Never use target columns, source identifiers as predictive features (unless a documented ablation explicitly requests them), or post-outcome fields in enrollment-stage models. Use SMOTE only inside training folds.

## Integration methodology

1. Inspect each dataset independently and record its citation, version, license, row count, fields, target values, missingness, and duplicates.
2. Map only semantically equivalent concepts through the versioned JSON mapping. The mapping response reports which physical columns generated each common feature.
3. Normalize academic scores to within-source percentile ranks; preserve raw inputs in the uploaded originals. Derived trend is latest minus earlier semester percentile.
4. Create provenance and source-specific missingness indicators. Dataset-only fields are retained when explicitly mapped; no records are matched across datasets.
5. Concatenate rows, retain outcome labels by default, and export a processed CSV plus original/source and combined statistics.
6. Fit imputers, encoders, scaling, feature selection and resampling on training folds only. Compare source-specific and pooled results; report cross-source transfer separately.

The proposal's mapping table provides a starting point, not proof that two similarly named fields are equivalent. Report pooled binary results alongside source-specific metrics and interpret the synthetic Kaggle source separately from UCI.

## Deliverables in this module

- `main.py`: FastAPI upload, metadata, validation, preview, integration and download endpoints.
- `pipeline.py`: CSV checks, statistics, feature mapping, safe derived features, integration and sklearn preprocessing factory.
- `preprocessing.py`: leakage-aware split and train-fit/test-transform export.
- `static/`: responsive dataset management UI.
- `config/feature_mapping.json`: editable, auditable source mapping and label policy.
- `data/`: runtime-generated uploads, metadata and processed exports (excluded from version control).

The web app does not download external data during upload or integration. Use `download_datasets.py` as a separate, reproducible acquisition step; the Kaggle package may require account approval.
