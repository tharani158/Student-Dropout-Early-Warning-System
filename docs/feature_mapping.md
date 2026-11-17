# Feature mapping register

| Harmonised concept | Kaggle synthetic source | UCI Portuguese source | Derivation / cautions |
| --- | --- | --- | --- |
| Age | Configure exact header | `Age at enrollment` | Numeric age in years |
| Gender | Configure exact header | `Gender` | Keep as categorical code unless dictionary confirms meaning |
| Scholarship | Configure exact header | `Scholarship holder` | Binary indicator |
| Parental education | Configure exact header | max of `Mother's qualification`, `Father's qualification` | Ordinal max is a project choice; retain raw parent fields for source analysis |
| Overall academic score | Configure CGPA column | Mean percentile of first and second semester grades | Percentiles computed independently within each source |
| Latest semester score | Configure semester GPA column | Percentile of `Curricular units 2nd sem (grade)` | Within-source percentile |
| Score trend | Semester GPA minus CGPA (confirm same scale) | Second-semester percentile minus first-semester percentile | Trend is not a raw-score subtraction across datasets |
| Engagement rate | Configure attendance rate | 1 − second-semester units without evaluation / second-semester units enrolled | Proxy, not a direct attendance measure; denominator zero becomes missing |
| Financial stress flag | Configure documented indicator | Debtor OR tuition fees not up to date | Must be interpreted consistently; proposal treats this as a proxy |
| Dataset source | `kaggle_synthetic` | `uci_portuguese` | Provenance flag; excluded from model features by default |
| Target (original) | Configure exact target and values | `Target` | Keep all original source labels in `target_original`; UCI three-class run stays separate |
| Target (binary) | Explicit label map | Dropout=1, Enrolled/Graduate=0 | Optional separate experiment; never overwrite original labels |

The JSON config is the executable register. Do not leave any `REPLACE_WITH_...` values in place for an integration run. Verify all aliases against the downloaded CSV headers and record dataset citation, release, license, and any deviations before proceeding. Shared concepts that are not truly comparable should be left unmapped instead of forced into a common column.
The executable mapping is [config/feature_mapping.json](../config/feature_mapping.json). It uses observed headers from the Kaggle v3 and UCI files. This conservative map is for an exploratory pooled experiment; source-specific modeling remains the primary comparison.

| Concept | Kaggle synthetic | UCI Portuguese | Interpretation |
|---|---|---|---|
| Age | `Age` | `Age at enrollment` | Years; verify prediction timing |
| Scholarship | `Scholarship` Yes/No → 1/0 | `Scholarship holder` 1/0 | Comparable binary concept |
| Overall score | `CGPA / 4` | mean first/second semester grade `/ 20` | Fixed grading-scale conversion; different academic constructs |
| Latest score | `Semester_GPA / 4` | second-semester grade `/ 20` | Fixed grading-scale conversion; available only after assessment |
| Engagement | `Attendance_Rate / 100` | Unmapped | UCI non-evaluation ratio is not direct attendance |
| Financial stress | Unmapped | Debtor OR fees not current | Kaggle income is not equivalent to tuition arrears |
| Gender | Unmapped | Unmapped | Verify source codes before a common representation |
| Parental education | Unmapped | Unmapped | UCI qualification codes are categories, not an ordinal numeric scale |
| Score trend | Unmapped | Unmapped | Semester versus cumulative GPA differs from UCI semester-to-semester change |
| Source | `kaggle_synthetic` | `uci_portuguese` | Provenance, excluded from default model features |

The score conversion divides each row by the known scale maximum and does not depend on other students. Do not compute percentiles or other fitted transformations before the train/test split. Scores are still measured differently, so pooled results require source-specific evaluation.

## Target policy

The `preserve` mode keeps Kaggle `Dropout` values 0/1 and UCI `Target` values Dropout/Graduate/Enrolled as original strings. The `binary_dropout` mode maps Kaggle 1 → 1 and 0 → 0, and UCI Dropout → 1 and Graduate → 0. **UCI Enrolled → null** because those students have no resolved dropout or graduation outcome at the snapshot. `preprocessing.py` excludes null targets from supervised training. The original uploaded CSVs remain unchanged.
