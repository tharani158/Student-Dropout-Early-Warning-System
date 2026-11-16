# Feature mapping register

| Harmonised concept | Kaggle synthetic source | UCI Portuguese source | Derivation / cautions |
|---|---|---|---|
| Age | `Age` | `Age at enrollment` | Numeric age in years; check prediction timing |
| Gender | Unmapped | Unmapped | Source coding needs a verified common definition |
| Scholarship | `Scholarship` Yes/No → 1/0 | `Scholarship holder` | Binary indicator |
| Parental education | Unmapped | Unmapped | Kaggle text categories and UCI codes are not directly equivalent; UCI codes are not a simple ordinal scale |
| Overall academic score | `CGPA` percentile | Mean percentile of first and second semester grades | Source-specific score definitions; percentiles computed independently |
| Latest semester score | `Semester_GPA` percentile | Percentile of `Curricular units 2nd sem (grade)` | Within-source percentile |
| Score trend | Unmapped | Unmapped | Kaggle semester/cumulative GPA and UCI semester grades do not define the same trend |
| Engagement rate | `Attendance_Rate` divided by 100 | Unmapped | Attendance is not equivalent to a UCI evaluation proxy |
| Financial stress flag | Unmapped | Debtor OR tuition fees not up to date | Kaggle family income is not equivalent to payment status |
| Dataset source | `kaggle_synthetic` | `uci_portuguese` | Provenance flag; excluded from model features by default |
| Target (original) | `Dropout`, values 0/1 | `Target`, values Dropout/Enrolled/Graduate | Keep original source labels; UCI three-class run stays separate |
| Target (binary) | 1=dropout, 0=non-dropout | Dropout=1, Enrolled/Graduate=0 | Optional separate experiment; original CSV remains unchanged |

The JSON config is the executable register, checked against the downloaded files on 2026-11-16. Verify aliases again when downloading a new version. Shared concepts that are not truly comparable stay unmapped.
