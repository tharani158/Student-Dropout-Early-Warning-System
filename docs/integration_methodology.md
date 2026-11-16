# Dataset Integration Methodology and Validation Record

## 1. Data Identity and Source Specifications

The project utilizes two primary dataset sources. The files were inspected on 2026-11-16; [EDA findings](eda_findings.md) record observed counts and checksums.

1. **UCI Portuguese Higher Education Dataset (`uci_portuguese.csv` after parsing the official semicolon-delimited file)**
   - **Source:** UCI Machine Learning Repository Dataset ID 697 (*Predict students' dropout and academic success*, Realinho et al., 2021).
   - **Dimensions:** 4,424 instances, 37 attributes.
   - **Characteristics:** Real-world higher education registry data from Portugal (2008–2019). Zero missing values. Zero duplicate rows.
   - **Target:** 3 distinct outcome classes: `Graduate` (2,209; 49.9%), `Dropout` (1,421; 32.1%), `Enrolled` (794; 18.0%).
   - **Grading Scale:** Portuguese national higher-education scale (0 to 20).

2. **Kaggle Synthetic Dropout Dataset (`kaggle_synthetic.csv`)**
   - **Source:** Kaggle (*Student Dropout Prediction Dataset*, meharshanali).
   - **Origin:** The linked public archive contained `student_dropout_dataset_v3.csv`; it was saved locally as `kaggle_synthetic.csv`.
   - **Dimensions:** 10,000 instances, 19 attributes.
   - **Characteristics:** Artificially generated student observations. 2,011 missing values across 4 features (`Family_Income`: 500, `Study_Hours_per_Day`: 500, `Stress_Index`: 500, `Parental_Education`: 511). Zero duplicate rows.
   - **Target:** Binary outcome: `0` (retained/non-dropout; 7,646; 76.5%) and `1` (dropout; 2,354; 23.5%).
   - **Identifier:** Contains `Student_ID` (1 to 10,000). **Exclusion policy:** Automatically omitted from all model inputs and feature mappings to prevent artificial identity memorization.
   - **Grading Scale:** US GPA scale (0.0 to 4.0).

---

## 2. Source-Specific Integrity vs. Integration Strategy

### Why Blind Concatenation is Scientifically Invalid
The two datasets represent fundamentally distinct student populations, feature spaces, and measurement scales:
- **Grading Systems:** UCI grades are European semester credits ($0\text{--}20$); Kaggle grades are US grade point averages ($0.0\text{--}4.0$).
- **Feature Semantics:** UCI records administrative course progression milestones (`Curricular units approved / evaluated / credited`) and national macroeconomics (`GDP`, `Inflation`, `Unemployment`). Kaggle records behavioral and lifestyle factors (`Study_Hours_per_Day`, `Attendance_Rate`, `Stress_Index`, `Internet_Access`).
- **Target Semantics:** UCI tracks active students (`Enrolled`), while Kaggle records a binary state.

### Recommended Experimental Protocol
1. **Source-Specific Benchmarks (Primary):** Member 3 models (Logistic Regression, KNN) are trained and benchmarked independently on:
   - UCI-alone (3-class preserved target, and binary dropout vs graduate).
   - Kaggle-alone (binary dropout).
2. **Integrated Harmonization (Exploratory / Secondary):** When both datasets are integrated via `/api/integrate`:
   - The conservative executable mapping includes `age`, `scholarship`, fixed-scale academic scores, and source-specific engagement/financial fields. Gender, parental education, and score trend remain unmapped pending semantic verification.
   - The provenance attribute `source` (`uci_portuguese` vs `kaggle_synthetic`) is strictly attached to every row and excluded from model inputs by default.
   - Transfer experiments and subgroup analyses can evaluate cross-dataset generalizability.

---

## 3. Target Harmonization and Resolving Active Students

To avoid label contamination, two explicit modes are supported:

1. **`target_mode="preserve"`:**
   - Retains the exact raw target strings for each source.
   - UCI outputs `Graduate`, `Dropout`, and `Enrolled`.
   - Kaggle outputs `0` and `1`.
   - Guarantees zero loss of target ground truth for multiclass tasks.

2. **`target_mode="binary_dropout"`:**
   - For Kaggle: `0` $\rightarrow 0$ (Retained), `1` $\rightarrow 1$ (Dropout).
   - For UCI: `Dropout` $\rightarrow 1$, `Graduate` $\rightarrow 0$, and `Enrolled` $\rightarrow \text{null}$ (`<NA>`).
   - **Critical Label Integrity:** `Enrolled` students have neither graduated nor dropped out. Treating `Enrolled` as `0` would falsely classify students who are still studying as graduates. By mapping `Enrolled` to `null`, `preprocessing.py` excludes unresolved cases when preparing binary training sets, ensuring models learn strictly from resolved outcomes.

---

## 4. Leakage-Free Preprocessing and Artifact Persistence

### Removal of Pre-Split Global Ranking
Previous implementations used global percentile ranking (`raw[c].rank(pct=True)`) during dataset integration, allowing the entire dataset (including held-out test rows) to influence training features.

**Current Leakage-Free Implementation:**
- All feature derivations in `pipeline.py` operate on row-level arithmetic within a single student's record ($row_i$):
  - `overall_academic_score`: Kaggle CGPA divided by 4; UCI row-level mean of Semester 1 and Semester 2 grades divided by 20.
  - `latest_semester_score`: The latest score divided by its fixed grading-scale maximum.
  - `financial_stress`: Row-level logical condition (`Debtor == 1` OR `Tuition fees up to date == 0`).
- No student record depends on another student record during feature extraction.

### Post-Split Transformations & Model Persistence
- In `preprocessing.py`:
  1. The dataset is partitioned into $80\%$ train and $20\%$ test partitions using stratified splitting (`train_test_split(..., stratify=y, random_state=42)`).
  2. Imputers (`SimpleImputer(strategy='median')` / mode) and scalers (`StandardScaler()`, `OneHotEncoder()`) are fitted **strictly on the training split** ($X_{\text{train}}$).
  3. The frozen transformation is applied to $X_{\text{test}}$.
  4. The fitted `ColumnTransformer` is persisted as `output_dir / "preprocessor.joblib"` using `joblib.dump()`.
  5. Member 3's backend inference service can reload `preprocessor.joblib` directly to transform new, incoming student data points at runtime.
