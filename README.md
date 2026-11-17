# EduGuard dataset management (Member 2)

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

Edit `config/feature_mapping.json` to use the exact source column headers. The UCI profile includes proposal-aligned features: age, gender, scholarship, higher parental qualification, within-source grade percentiles, semester percentile trend, engagement proxy, and financial stress flag. Percentile ranks are computed within each source independently because grading scales differ. A feature should only be mapped when its definition matches; otherwise set it to null/omit it and document the difference. The `source` field is provenance, not a student identifier.

The Kaggle source is identified by the brief, but its page does not provide a readable schema through this environment. Use the downloader's local inspection report (or the uploaded dataset preview) and replace its target/feature aliases only after inspecting its exact headers and data dictionary. Do not guess labels, columns, or equivalence.

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

1. Verify the prepared dataset and its target labels.
2. Conduct exploratory analysis and inspect class distributions.
3. Select the appropriate prediction target and input features.
4. Split the data into training and testing sets using stratification where feasible.
5. Fit preprocessing and model training using training data only.
6. Train Logistic Regression and KNN independently.
7. Evaluate both models using consistent metrics and validation procedures.
8. Compare model performance and select a suitable model.
9. Save the complete fitted preprocessing and model pipeline.
10. Integrate the selected models with the FastAPI prediction service.

**Important dataset considerations:**

- UCI dataset 697 contains three original outcomes: Dropout, Graduate, and Enrolled.
- For a binary dropout experiment, Enrolled records must be handled according to the documented target policy rather than automatically treating them as non-dropouts.
- Kaggle and UCI experiments should initially be evaluated separately.
- Pooled or cross-source experiments should be reported separately because similar feature names do not necessarily represent equivalent measurements.
- Features unavailable at the intended prediction time must not be used. In particular, post-outcome academic information must be excluded from an early-stage prediction model.

## Expected Deliverables

- Logistic Regression training implementation.
- KNN training implementation.
- Model evaluation and comparison reports.
- Confusion matrices and performance visualisations.
- Saved model and preprocessing pipelines.
- Dropout prediction functionality.
- FastAPI prediction and evaluation integration.
- Frontend prediction and model comparison interfaces.
- Model-related automated tests and documentation.
