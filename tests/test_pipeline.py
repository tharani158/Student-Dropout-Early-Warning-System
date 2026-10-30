import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline import DatasetError, MAX_UPLOAD_BYTES, inspect_dataframe, integrate_datasets, load_dataset, validate_upload


class PipelineTests(unittest.TestCase):
    def test_upload_file_type_contract(self):
        validate_upload("students.csv", "text/csv")
        validate_upload("students.csv", "text/csv", size_bytes=1024)
        with self.assertRaises(DatasetError):
            validate_upload("students.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with self.assertRaisesRegex(DatasetError, "20 MB"):
            validate_upload("too-large.csv", "text/csv", size_bytes=MAX_UPLOAD_BYTES + 1)

    def test_validation_reports_missing_values(self):
        result = inspect_dataframe(pd.DataFrame({"age": [20, 20], "status": ["Dropout", None]}))
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["duplicate_rows"], 0)
        self.assertEqual(result["missing_cells"], 1)

    def test_integration_concatenates_and_preserves_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b, mapping = root / "a.csv", root / "b.csv", root / "mapping.json"
            pd.DataFrame({"Age": [18], "Outcome": ["Dropout"]}).to_csv(a, index=False)
            pd.DataFrame({"Age": [19], "Outcome": ["Graduate"]}).to_csv(b, index=False)
            mapping.write_text(json.dumps({"datasets": {
                "a": {"target": "Outcome", "features": {"age": "Age"}},
                "b": {"target": "Outcome", "features": {"age": "Age"}}
            }}), encoding="utf-8")
            result = integrate_datasets([{"path": str(a), "source": "a"},
                                         {"path": str(b), "source": "b"}], mapping)
            self.assertEqual(len(result["data"]), 2)
            self.assertEqual(result["data"]["source"].tolist(), ["a", "b"])
            self.assertEqual(result["data"]["target_original"].tolist(), ["Dropout", "Graduate"])
            self.assertEqual(result["statistics"]["target_counts"], {"Dropout": 1, "Graduate": 1})

    def test_integration_rejects_unmapped_binary_label(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data, mapping = root / "a.csv", root / "mapping.json"
            pd.DataFrame({"Outcome": ["Unknown"]}).to_csv(data, index=False)
            mapping.write_text(json.dumps({"datasets": {"a": {
                "target": "Outcome", "features": {}, "binary_target": {"Dropout": 1}
            }}}), encoding="utf-8")
            with self.assertRaisesRegex(DatasetError, "Unmapped target"):
                integrate_datasets([{"path": str(data), "source": "a"},
                                    {"path": str(data), "source": "a"}], mapping, "binary_dropout")

    def test_duplicate_headers_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("age,age\n20,21\n", encoding="utf-8")
            with self.assertRaisesRegex(DatasetError, "Duplicate column"):
                load_dataset(path)


if __name__ == "__main__":
    unittest.main()
