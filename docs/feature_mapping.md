# Feature Mapping Register

| Harmonised Concept | Kaggle Synthetic Source | UCI Portuguese Source | Derivation / Cautions |
|---|---|---|---|
| **Age** | `Age` | `Age at enrollment` | Numeric age in years. |
| **Gender** | `Gender` | `Gender` | In Kaggle: string ('Male', 'Female'). In UCI: binary integer code (1: male, 0: female). Handled by downstream encoders. |
| **Scholarship** | `Scholarship` | `Scholarship holder` | In Kaggle: string ('Yes', 'No'). In UCI: binary integer (1, 0). |
| **Parental Education** | `Parental_Education` | `Mother's qualification`, `Father's qualification` | In Kaggle: string educational tier ('High School', 'Bachelor', etc.). In UCI: max of mother's and father's qualification codes (ordinal integer scale). |
| **Overall Academic Score** | `CGPA` | Mean of `Curricular units 1st sem (grade)` and `Curricular units 2nd sem (grade)` | Row-level calculation. Zero cross-row percentile leakage. |
| **Latest Semester Score** | `Semester_GPA` | `Curricular units 2nd sem (grade)` | Most recent semester academic performance score. |
| **Score Trend** | Difference: `Semester_GPA` minus `CGPA` | Difference: `Curricular units 2nd sem (grade)` minus `Curricular units 1st sem (grade)` | Row-level difference measuring academic trajectory. Positive indicates improvement; negative indicates academic decline. |
| **Engagement Rate** | `Attendance_Rate` | $1 - (\text{2nd sem units without evaluations} / \text{2nd sem units enrolled})$ | In Kaggle: percentage attendance rate (38.2 to 100.0). In UCI: participation proxy based on non-evaluation ratios. |
| **Financial Stress Flag** | `null` (unmapped) | `Debtor` OR `Tuition fees up to date == 0` | UCI derives a binary financial stress indicator from tuition arrears and debtor status. Kaggle has no comparable debt/tuition metric; setting to null maintains feature fidelity without fabricating data. |
| **Dataset Source** | `kaggle_synthetic` | `uci_portuguese` | Provenance identifier. Automatically excluded from predictive model inputs by default. |
| **Target (Original)** | `Dropout` | `Target` | Preserves source-specific targets: UCI retains all 3 classes ('Graduate', 'Dropout', 'Enrolled'); Kaggle retains binary values ('0', '1'). |
| **Target (Binary)** | `{"0": 0, "1": 1}` | `{"Dropout": 1, "Graduate": 0, "Enrolled": null}` | Standard binary dropout target. In UCI, 'Enrolled' students (actively studying) are explicitly mapped to null (<NA>) to avoid falsely conflating active students with graduates. |

## Target Harmonization Policy

1. **`target_mode="preserve"`:**
   - Retains original source outcome strings.
   - For UCI: preserves the three distinct outcomes: `Graduate` (2,209), `Dropout` (1,421), and `Enrolled` (794).
   - For Kaggle: preserves original binary categories (`0`: 7,646, `1`: 2,354).

2. **`target_mode="binary_dropout"`:**
   - For Kaggle: maps `0` to `0` (retained) and `1` to `1` (dropout).
   - For UCI: maps `Dropout` to `1`, `Graduate` to `0`, and `Enrolled` to `null` (`<NA>`).
   - Active students who have neither graduated nor dropped out are not forced into the negative class. When preparing training sets in `preprocessing.py`, unresolved (`null`) records are excluded from binary supervised training, preventing label contamination.

## Leakage Prevention Policy

- All feature engineering operations in `pipeline.py` operate strictly within a single student record (row-level arithmetic).
- Pre-split global percentile ranking has been eliminated.
- Scaling (`StandardScaler`), median imputation, and one-hot encoding are fitted strictly on training folds in `preprocessing.py`.
- The fitted `ColumnTransformer` is persisted as `preprocessor.joblib` for inference reuse.
