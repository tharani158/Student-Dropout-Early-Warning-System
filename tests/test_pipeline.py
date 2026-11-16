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

    def test_actual_feature_mapping_has_no_placeholders(self):
        base_dir = Path(__file__).resolve().parent.parent
        mapping_file = base_dir / "config" / "feature_mapping.json"
        text = mapping_file.read_text(encoding="utf-8")
        self.assertNotIn("REPLACE_WITH", text, "Found unresolved REPLACE_WITH placeholders in feature_mapping.json")

    def test_actual_kaggle_synthetic_csv_and_mapping(self):
        base_dir = Path(__file__).resolve().parent.parent
        mapping_file = base_dir / "config" / "feature_mapping.json"
        kaggle_csv = base_dir / "data" / "raw" / "kaggle_synthetic.csv"
        self.assertTrue(kaggle_csv.exists(), "data/raw/kaggle_synthetic.csv does not exist")
        df = load_dataset(kaggle_csv)
        self.assertEqual(len(df), 10000)
        self.assertEqual(len(df.columns), 19)

        result = integrate_datasets([{"path": str(kaggle_csv), "source": "kaggle_synthetic"}],
                                    mapping_file, target_mode="binary_dropout")
        self.assertEqual(len(result["data"]), 10000)
        counts = result["statistics"]["target_counts"]
        self.assertEqual(counts.get("0"), 7646)
        self.assertEqual(counts.get("1"), 2354)

    def test_actual_uci_target_harmonization_preserves_three_classes_and_binary(self):
        base_dir = Path(__file__).resolve().parent.parent
        mapping_file = base_dir / "config" / "feature_mapping.json"
        uci_csv = base_dir / "data" / "raw" / "student_dropout_dataset_cleaned.csv"
        self.assertTrue(uci_csv.exists(), "data/raw/student_dropout_dataset_cleaned.csv does not exist")

        # 1. Preserved mode: 3 classes
        res_pres = integrate_datasets([{"path": str(uci_csv), "source": "uci_portuguese"}],
                                      mapping_file, target_mode="preserve")
        self.assertEqual(len(res_pres["data"]), 4424)
        pres_counts = res_pres["statistics"]["target_counts"]
        self.assertEqual(pres_counts.get("Graduate"), 2209)
        self.assertEqual(pres_counts.get("Dropout"), 1421)
        self.assertEqual(pres_counts.get("Enrolled"), 794)

        # 2. Binary mode: Enrolled mapped to null, not Graduate
        res_bin = integrate_datasets([{"path": str(uci_csv), "source": "uci_portuguese"}],
                                     mapping_file, target_mode="binary_dropout")
        self.assertEqual(len(res_bin["data"]), 4424)
        bin_counts = res_bin["statistics"]["target_counts"]
        self.assertEqual(bin_counts.get("0"), 2209)
        self.assertEqual(bin_counts.get("1"), 1421)
        # Enrolled must be null (unresolved / omitted from binary training), not 0
        self.assertEqual(bin_counts.get("null"), 794)

    def test_preprocessing_saves_reusable_preprocessor_without_leakage(self):
        import joblib
        from preprocessing import split_and_transform

        base_dir = Path(__file__).resolve().parent.parent
        mapping_file = base_dir / "config" / "feature_mapping.json"
        kaggle_csv = base_dir / "data" / "raw" / "kaggle_synthetic.csv"

        with tempfile.TemporaryDirectory() as td:
            temp_path = Path(td)
            res = integrate_datasets([{"path": str(kaggle_csv), "source": "kaggle_synthetic"}],
                                     mapping_file, target_mode="binary_dropout")
            integrated_csv = temp_path / "kaggle_int.csv"
            res["data"].to_csv(integrated_csv, index=False)

            exp_dir = temp_path / "exp"
            info = split_and_transform(integrated_csv, "target_binary_dropout", exp_dir)
            self.assertEqual(info["train_rows"], 8000)
            self.assertEqual(info["test_rows"], 2000)

            prep_file = exp_dir / "preprocessor.joblib"
            self.assertTrue(prep_file.exists(), "preprocessor.joblib was not saved")

            loaded_prep = joblib.load(prep_file)
            test_df = pd.read_csv(integrated_csv).drop(columns=["target_binary_dropout", "source"]).head(5)
            transformed = loaded_prep.transform(test_df)
            self.assertEqual(transformed.shape[0], 5)


if __name__ == "__main__":
    unittest.main()
