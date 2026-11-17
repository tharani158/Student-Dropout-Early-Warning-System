# Member 1: dashboard and exploratory data analysis

Real-data measurements from the two project links are in [eda_findings.md](eda_findings.md).

## Scope and handoff

The dashboard summarizes uploaded datasets; the profiler inspects raw rows without changing them. The dashboard shows dataset count, record count, sum of column counts, missing cells, outcome distribution for a selected dataset, dataset comparison, recent uploads and integration activity. A selected profile shows each column's type, missingness, unique count, frequent values, numeric summary and IQR outliers. The API returns up to 30 strongest Pearson correlations between numeric columns.

`total_features` in the dashboard is the sum of uploaded column counts, so common columns in two files are counted twice. For a single dataset, the profiler's `feature_count` excludes an identified target column. Each chart uses the raw uploaded CSV and should be interpreted per source. The outcome selector detects common labels (`Target`, `Outcome`, `Status`, `Dropout`); pass `?target=ExactColumnName` to the profile or class-distribution API for another name.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/`, choose **Dataset management**, and upload the Kaggle CSV and normalized UCI CSV with the correct source. Return to **Dashboard** for charts and profiling. Run `jupyter lab notebooks/01_student_data_eda.ipynb`; set `CSV_PATH` and `TARGET` in its first code cell. Run it once per source, then open `notebooks/02_dataset_comparison.ipynb` for side-by-side charts. The notebook works with a file in `data/raw/` or an explicit upload path.

For PostgreSQL, create a database and set `DATABASE_URL=postgresql://user:password@localhost:5432/eduguard` before starting the server. The app creates its `eduguard_state` table and stores metadata and activity as JSONB. Leave `DATABASE_URL` unset for the existing local JSON store. Uploaded CSV bytes remain in `data/uploads/` in either mode; mount or back up that directory for deployment. Existing `data/metadata.json` is not automatically migrated into PostgreSQL. Configure the database before the first upload in that environment.

## API contracts

| Endpoint | Result |
|---|---|
| `GET /api/dashboard/summary` | Totals, per-dataset comparison and class counts, latest activity |
| `GET /api/datasets/{id}/profile` | Full quality profile; optional `target` query |
| `GET /api/datasets/{id}/statistics` | Alias of profile |
| `GET /api/datasets/{id}/class-distribution` | Target name and label counts; optional `target` query |
| `GET /api/datasets/{id}/feature-groups` | Source-specific predictor groups and UCI stage lists |
| `POST /api/activities/model` | Log a training action with JSON such as `{"model":"Logistic Regression","status":"evaluated"}` |

Other upload and integration endpoints remain documented in the main README. For large production datasets, cache the dashboard summary after uploads because it currently rereads each CSV to compute class counts.

## EDA method

1. Record each dataset's source, version, license, download date, exact column names and target definition. Treat the UCI three-class data and Kaggle synthetic data separately at first.
2. Inspect shape, sample rows and data types. Check numeric-looking IDs and category codes against the data dictionary before interpreting them as continuous variables.
3. Count missing cells by feature, exact duplicate rows, unique values and class proportions. Investigate suspicious duplicates before dropping them.
4. Plot key numeric distributions and box plots. The profiler flags points outside 1.5 times the interquartile range; these may be valid students, so do not automatically delete them.
5. Plot correlations as exploratory descriptions. Pearson coefficients on category codes may be misleading. Check outcome relationships only for features available at the intended prediction time.
6. Save the notebook's profile and feature-group manifest JSON for the ML team. Split into train and test before fitting imputation, scaling or feature selection. Keep the held-out test data untouched until final evaluation.

## ML principle for this project

This is supervised classification: each historical student row has measurements and a known outcome. A model learns a mapping from measurements available at prediction time to a class or dropout probability, then is evaluated on unseen rows. The UCI outcome has **Dropout**, **Enrolled**, and **Graduate** classes. A separate binary task can treat Dropout as positive, but it changes the question and requires an explicit label policy. Do not train on the target itself, identifiers, final grades, or later semester information when predicting at enrollment. Use a stratified split where possible, train preprocessing only on training folds, and compare a simple baseline with more complex models. Report class-specific recall, precision, F1, confusion matrix and PR-AUC for binary dropout; include calibration and per-source results before choosing an intervention threshold. A risk score supports human review, not an automatic decision about a student.

## Evidence for final report

After the real CSVs are available, record the exact row and column counts, each outcome proportion, missingness, duplicate count, top outlier features, important feature distributions, and any confirmed impossible values. Capture dashboard overview, selected class chart, comparison chart, profile table, and notebook figures. State dataset versions and a reproducible command. Do not present fixture counts or unrun notebook cells as findings.

Run tests with `python -m unittest discover -s tests -v`.
