# EDA findings from the two project datasets

Downloaded on 2026-11-16 from [Kaggle's Student Dropout Prediction Dataset](https://www.kaggle.com/datasets/meharshanali/student-dropout-prediction-dataset) and [UCI dataset 697](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success). The Kaggle archive contained `student_dropout_dataset_v3.csv`; UCI's ZIP contained semicolon-delimited `data.csv`. For this project, the UCI file was parsed with `sep=";"`, its header whitespace was stripped, and it was saved as `data/raw/uci_portuguese.csv`. The unmodified UCI file is kept as `data/raw/uci_official_semicolon.csv` locally. Raw files are excluded from Git.

| Measure | Kaggle synthetic | UCI Portuguese |
|---|---:|---:|
| Students | 10,000 | 4,424 |
| Columns including target | 19 | 37 |
| Missing cells | 2,011 | 0 |
| Exact duplicate rows | 0 | 0 |
| Target | `Dropout` (0/1) | `Target` (three classes) |

Kaggle's target has **2,354 dropout (23.54%)** and **7,646 non-dropout (76.46%)** records. UCI has **1,421 Dropout (32.12%)**, **794 Enrolled (17.95%)**, and **2,209 Graduate (49.93%)** records. These percentages describe different source populations and target definitions, so their difference is not a cross-country prevalence estimate. The dashboard's 14,424 total records and 56 total columns are sums across files; 56 does not mean 56 distinct model features.

Kaggle's missing values occur in `Family_Income` (500), `Study_Hours_per_Day` (500), `Stress_Index` (500), and `Parental_Education` (511). Its `Student_ID` is unique for all 10,000 rows and should be excluded from model predictors. The IQR rule flags 604 `Family_Income` values, 86 study-hour values, and 57 attendance values; inspect their validity before any removal. UCI's site reports no missing values, matching the downloaded file. Its numeric-coded categories need a data dictionary rather than numeric outlier or Pearson interpretation. Many UCI semester fields measure progress after enrollment and must be omitted from an enrollment-time model.

In Kaggle, `Semester_GPA` and `CGPA` have Pearson **r = 0.999**. The simple numeric correlation between `GPA` and the binary dropout label is **r = −0.460**; descriptive group means are CGPA 1.44 for dropout and 2.56 for non-dropout. These observations do not establish a causal relationship or generalize from synthetic data to real students. UCI mean second-semester grade is 5.90 for Dropout, 11.12 for Enrolled, and 12.70 for Graduate. Those are post-enrollment measurements and useful only for predictions made after the second semester. UCI first and second semester grades correlate at **r = 0.837**. All correlations here are descriptive.

The profile JSON files are generated locally at `data/processed/kaggle_synthetic_profile.json` and `data/processed/uci_portuguese_profile.json`. Re-run the notebooks for plots and inspect the source-specific feature dictionary before final model selection. The integration mapping recognizes Kaggle's actual `Dropout` 0/1 labels, normalizes `Scholarship` Yes/No, and divides academic scores by fixed source-scale maxima. Fields with unclear equivalence are left unmapped. The pooled binary export contains 3,775 dropout labels, 9,855 resolved non-dropout labels, and 794 unresolved UCI Enrolled outcomes. Training preparation excludes the unresolved rows; source-specific evaluation remains necessary.

## Proposal alignment and model handoff

The proposal calls for UCI prediction at enrollment, after semester one, and after semester two. The audited [feature-group manifest](../config/feature_groups.json) provides **24 enrollment**, **30 through semester one**, and **36 through semester two** predictors. Kaggle has **17 predictors** after excluding `Student_ID` and the target, grouped as background (6), behavioral (7), and academic (4). It has one observation time and should use feature-group ablation rather than UCI-style stage claims. The manifest is available from `GET /api/datasets/{id}/feature-groups` and is included in the notebook's saved handoff JSON.

The proposal's projected 40-column combined table is a design estimate, not an observed dataset shape. The current conservative harmonization emits 10 columns, including source, binary target, and missingness flags. It does not claim that differently defined parental education, gender, attendance, or financial indicators are equivalent. A broader feature-engineering experiment is work for the integration/model team after meanings and prediction timing are confirmed. UCI `Enrolled` describes students still enrolled at the outcome snapshot, so the current binary policy leaves them unresolved instead of treating them as graduates or resolved non-dropouts.

The report figures are in [figures](figures/). Start with [class counts](figures/comparison_01.png) and [missingness](figures/comparison_02.png). `scripts/run_eda.py` executes both notebooks and regenerates all figures. For UCI, the categorical code descriptions on the [UCI dataset page](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success) should guide interpretation; numeric code magnitude is not a meaningful order for many fields.

## Reproducibility

- Kaggle CSV SHA-256: `27aac8b1289cdb3c21d0b031c42bb957af9e33d9c1f123b73952deef87e4a962`
- UCI original CSV SHA-256: `3ef126de5cefff26eb11fbb4237f1a1401cb64b488e2f1d598c23cedeb4c45ae`
- UCI normalized CSV SHA-256: `1b1cef8ac84b532c1124123c060f2da6da7ba9bfec54f4b3713dc31f1610340c`

The UCI dataset is credited to Realinho, Vieira Martins, Machado, and Baptista (2021), DOI [10.24432/C5MC89](https://doi.org/10.24432/C5MC89), under CC BY 4.0. Check and record the Kaggle page's license before redistributing its CSV.
