# Feature mapping register

| Harmonised concept | Kaggle synthetic source | UCI Portuguese source | Derivation / cautions |
|---|---|---|---|
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
