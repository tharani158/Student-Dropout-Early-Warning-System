import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

import main


class DatasetDeleteTests(unittest.TestCase):
    def test_root_serves_login_and_dashboard_route_serves_workspace(self):
        self.assertEqual(Path(main.login_page().path), main.BASE_DIR / "static" / "login.html")
        self.assertEqual(Path(main.dashboard().path), main.BASE_DIR / "static" / "index.html")

    def test_delete_removes_dataset_file_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            upload_dir = Path(folder) / "uploads"
            upload_dir.mkdir()
            metadata_file = Path(folder) / "metadata.json"
            dataset_path = upload_dir / "dataset.csv"
            dataset_path.write_text("age\n20\n", encoding="utf-8")
            metadata_file.write_text(json.dumps({"datasets": [{
                "id": "dataset-id", "path": str(dataset_path.resolve())
            }]}), encoding="utf-8")

            with patch.object(main, "UPLOAD_DIR", upload_dir), patch.object(main, "META_FILE", metadata_file):
                result = main.delete_dataset("dataset-id")

                self.assertEqual(result, {"status": "deleted", "id": "dataset-id"})
                self.assertFalse(dataset_path.exists())
                self.assertEqual(main.read_metadata()["datasets"], [])

    def test_delete_returns_not_found_for_unknown_dataset(self):
        with tempfile.TemporaryDirectory() as folder:
            metadata_file = Path(folder) / "metadata.json"
            metadata_file.write_text(json.dumps({"datasets": []}), encoding="utf-8")

            with patch.object(main, "META_FILE", metadata_file):
                with self.assertRaises(HTTPException) as error:
                    main.delete_dataset("missing")

            self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
