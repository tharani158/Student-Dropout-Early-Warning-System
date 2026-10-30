"""Leakage-aware train/test preprocessing for EduGuard CSV experiments.

Example: python preprocessing.py data/processed/integrated_x.csv target_binary_dropout
Fit all imputers, encoders, and scalers on the training split only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def split_and_transform(csv_path: Path, target: str, output_dir: Path, test_size: float = .2, seed: int = 42) -> dict:
    frame = pd.read_csv(csv_path, low_memory=False)
    if target not in frame:
        raise ValueError(f"Target '{target}' was not found. Available columns: {list(frame.columns)}")
    if target == "target_original" and frame[target].nunique(dropna=True) > 2:
        # This is valid for the UCI three-class task; stratify on all observed labels.
        pass
    data = frame.loc[frame[target].notna()].copy()
    y = data.pop(target)
    # Remove other target columns to prevent accidental label leakage.
    data = data.drop(columns=[c for c in ("target_original", "target_binary_dropout") if c in data], errors="ignore")
    # Source is retained for stratification/reporting, but excluded from model inputs by default.
    source = data.pop("source") if "source" in data else None
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    row_ids = pd.Series(range(len(data)), index=data.index)
    train_ids, test_ids = train_test_split(row_ids, test_size=test_size, random_state=seed, stratify=stratify)
    X_train, X_test = data.loc[train_ids.index], data.loc[test_ids.index]
    y_train, y_test = y.loc[train_ids.index], y.loc[test_ids.index]
    if source is not None:
        # Keep source representation for analysis and source-stratified checks, not model input.
        source_train, source_test = source.loc[train_ids.index], source.loc[test_ids.index]
    else:
        source_train = source_test = None

    numeric_cols = X_train.select_dtypes(include="number").columns.tolist()
    categorical_cols = X_train.select_dtypes(exclude="number").columns.tolist()
    numeric = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    prep = ColumnTransformer([("numeric", numeric, numeric_cols), ("categorical", categorical, categorical_cols)])
    # Fit once on training rows. The held-out test data does not affect learned preprocessing.
    train_values = prep.fit_transform(X_train)
    test_values = prep.transform(X_test)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(train_values, columns=prep.get_feature_names_out()).to_csv(output_dir / "X_train.csv", index=False)
    pd.DataFrame(test_values, columns=prep.get_feature_names_out()).to_csv(output_dir / "X_test.csv", index=False)
    y_train.to_csv(output_dir / "y_train.csv", index=False, header=[target])
    y_test.to_csv(output_dir / "y_test.csv", index=False, header=[target])
    if source_train is not None:
        pd.DataFrame({"source": source_train}).to_csv(output_dir / "source_train.csv", index=False)
        pd.DataFrame({"source": source_test}).to_csv(output_dir / "source_test.csv", index=False)
    return {"train_rows": len(X_train), "test_rows": len(X_test), "features_after_encoding": len(prep.get_feature_names_out()),
            "target": target, "source_excluded_from_model_features": source is not None,
            "preprocessor": prep}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("target")
    parser.add_argument("--output", type=Path, default=Path("data/experiments"))
    parser.add_argument("--test-size", type=float, default=.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    info = split_and_transform(args.csv, args.target, args.output, args.test_size, args.seed)
    print({k: v for k, v in info.items() if k != "preprocessor"})
