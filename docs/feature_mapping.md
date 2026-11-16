# Feature mapping register

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
