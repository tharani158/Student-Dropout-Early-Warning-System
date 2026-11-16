"""Auditable feature availability lists for downstream model experiments."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

CONFIG = Path(__file__).resolve().parent / "config" / "feature_groups.json"


def feature_groups(frame: pd.DataFrame, source: str) -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    groups = config.get(source)
    if not groups:
        return {"source": source, "groups": {}, "stages": {}, "unassigned_columns": list(frame.columns)}
    declared = [column for values in groups.values() for column in values]
    missing = set(declared) - set(frame.columns)
    if missing:
        raise ValueError(f"Feature-group columns missing from {source}: {sorted(missing)}")
    target = "Target" if source == "uci_portuguese" else "Dropout"
    excluded = {target, "Student_ID"}
    unassigned = sorted(set(frame.columns) - set(declared) - excluded)
    stages = {}
    if source == "uci_portuguese":
        stages = {"enrollment": groups["enrollment"],
                  "after_first_semester": groups["enrollment"] + groups["first_semester"],
                  "after_second_semester": groups["enrollment"] + groups["first_semester"] + groups["second_semester"]}
    return {"source": source, "target": target, "excluded": sorted(excluded & set(frame.columns)),
            "groups": groups, "stages": stages, "unassigned_columns": unassigned}
