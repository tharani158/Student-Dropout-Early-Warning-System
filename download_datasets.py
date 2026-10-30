"""Download the two cited project datasets and save local inspection reports.

Kaggle downloads may require Kaggle account/consent. Use `kagglehub login` or the
Kaggle API credentials documented by Kaggle before running this script.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"


def inspect(frame: pd.DataFrame, target: str | None = None) -> dict:
    report = {
        "rows": len(frame), "columns_count": len(frame.columns),
        "columns": [{"name": str(c), "dtype": str(frame[c].dtype),
                     "missing": int(frame[c].isna().sum()),
                     "unique": int(frame[c].nunique(dropna=True))} for c in frame.columns],
        "duplicate_rows": int(frame.duplicated().sum()),
    }
    if target and target in frame:
        report["target_column"] = target
        report["target_counts"] = frame[target].astype("string").value_counts(dropna=False).to_dict()
    return report


def download_uci() -> tuple[Path, dict]:
    from ucimlrepo import fetch_ucirepo

    dataset = fetch_ucirepo(id=697)
    features = dataset.data.features.reset_index(drop=True)
    targets = dataset.data.targets.reset_index(drop=True)
    frame = pd.concat([features, targets], axis=1)
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "uci_portuguese.csv"
    frame.to_csv(path, index=False)
    target = "Target" if "Target" in frame else str(targets.columns[0])
    report = inspect(frame, target)
    report.update({"source": "UCI dataset 697", "license": "CC BY 4.0",
                   "citation": "Realinho et al. (2021), DOI: 10.24432/C5MC89"})
    return path, report


def download_kaggle() -> tuple[Path, dict]:
    import kagglehub

    downloaded = Path(kagglehub.dataset_download("meharshanali/student-dropout-prediction-dataset"))
    csv_files = sorted(downloaded.rglob("*.csv"))
    if len(csv_files) != 1:
        raise RuntimeError(f"Expected one CSV in Kaggle download, found {len(csv_files)}: {[p.name for p in csv_files]}")
    frame = pd.read_csv(csv_files[0], low_memory=False)
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "kaggle_synthetic.csv"
    shutil.copy2(csv_files[0], path)
    candidates = [c for c in frame.columns if str(c).strip().lower() in {"dropout", "target", "label", "status"}]
    target = candidates[0] if len(candidates) == 1 else None
    report = inspect(frame, target)
    report.update({"source": "Kaggle meharshanali/student-dropout-prediction-dataset",
                   "downloaded_filename": csv_files[0].name,
                   "dataset_page": "https://www.kaggle.com/datasets/meharshanali/student-dropout-prediction-dataset"})
    return path, report


def main() -> None:
    report = {"kaggle": None, "uci": None}
    for key, action in (("kaggle", download_kaggle), ("uci", download_uci)):
        try:
            path, details = action()
            report[key] = {"file": str(path.relative_to(ROOT)), **details}
            print(f"{key.upper()}: {path} ({details['rows']} rows, {details['columns_count']} columns)")
            print("Headers:", ", ".join(str(c["name"]) for c in details["columns"]))
        except Exception as exc:
            report[key] = {"error": str(exc)}
            print(f"{key.upper()} download/inspection failed: {exc}")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "inspection_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Inspection report: {RAW / 'inspection_report.json'}")
    if any(report[key].get("error") for key in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
