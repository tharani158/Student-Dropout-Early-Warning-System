import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

import main
from profiling import profile_dataframe
from feature_groups import feature_groups


class ProfilingTests(unittest.TestCase):
    def test_missing_duplicates_classes_and_types(self):
        frame = pd.DataFrame({"Age": [18, 18, 20, 90, None],
                              "Target": ["Dropout", "Dropout", "Graduate", "Graduate", "Enrolled"]})
        result = profile_dataframe(frame)
        self.assertEqual(result["missing_cells"], 1)
        self.assertEqual(result["duplicate_rows"], 1)
        self.assertEqual(result["target_column"], "Target")
        self.assertEqual(result["feature_count"], 1)
        self.assertEqual(result["columns"][0]["type"], "numeric")
        self.assertEqual({x["label"] for x in result["class_distribution"]},
                         {"Dropout", "Graduate", "Enrolled"})

    def test_outlier_flag_and_missing_target(self):
        frame = pd.DataFrame({"Score": [1, 2, 2, 3, 100], "Outcome": ["A", "A", "B", "B", None]})
        result = profile_dataframe(frame)
        self.assertEqual(result["columns"][0]["outlier_count"], 1)
        self.assertTrue(any("outcome labels" in issue for issue in result["quality_issues"]))

    def test_real_source_feature_availability(self):
        raw = Path(__file__).resolve().parents[1] / "data" / "raw"
        if not (raw / "uci_portuguese.csv").exists():
            self.skipTest("Downloaded data is not stored in Git")
        uci = feature_groups(pd.read_csv(raw / "uci_portuguese.csv"), "uci_portuguese")
        kaggle = feature_groups(pd.read_csv(raw / "kaggle_synthetic.csv"), "kaggle_synthetic")
        self.assertEqual([len(x) for x in uci["stages"].values()], [24, 30, 36])
        self.assertEqual(sum(len(x) for x in kaggle["groups"].values()), 17)
        self.assertEqual(uci["unassigned_columns"], [])
        self.assertEqual(kaggle["unassigned_columns"], [])
        self.assertNotIn("Target", uci["stages"]["after_second_semester"])
        self.assertNotIn("Student_ID", sum(kaggle["groups"].values(), []))


class DashboardApiTests(unittest.TestCase):
    def test_summary_and_profile_use_uploaded_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv = root / "sample.csv"
            pd.DataFrame({"Age": [18, 19, 19], "Target": ["Dropout", "Graduate", "Graduate"]}).to_csv(csv, index=False)
            state = {"datasets": [{"id": "one", "filename": "sample.csv", "source": "test",
                "path": str(csv), "rows": 3, "columns": 2, "uploaded_at": "2026-01-01T00:00:00Z",
                "validation": {"missing_cells": 0, "duplicate_rows": 0}}], "activities": []}
            meta = root / "metadata.json"
            meta.write_text(json.dumps(state), encoding="utf-8")
            with patch.object(main, "META_FILE", meta), patch.dict("os.environ", {}, clear=False):
                client = TestClient(main.app)
                summary = client.get("/api/dashboard/summary")
                self.assertEqual(summary.status_code, 200)
                self.assertEqual(summary.json()["total_records"], 3)
                self.assertEqual(summary.json()["datasets"][0]["class_distribution"][0]["label"], "Graduate")
                self.assertEqual(client.get("/api/datasets/one/profile").json()["feature_count"], 1)
                self.assertEqual(client.get("/api/datasets/one/class-distribution").json()["classes"][1]["count"], 1)
                self.assertEqual(client.get("/api/datasets/one/profile?target=unknown").status_code, 422)
                self.assertEqual(client.get("/api/datasets/missing/profile").status_code, 404)
                self.assertEqual(client.post("/api/activities/model", json={"model": "Baseline", "status": "evaluated"}).status_code, 200)
                self.assertEqual(client.get("/api/dashboard/summary").json()["recent_activities"][0]["kind"], "model")


if __name__ == "__main__":
    unittest.main()
