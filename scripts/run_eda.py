"""Execute both EDA notebooks against the downloaded datasets and save report figures."""
from __future__ import annotations

import base64
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
OUTPUT = ROOT / "data" / "processed" / "executed_notebooks"
FIGURES = ROOT / "docs" / "figures"


def execute(name: str, csv_name: str | None = None) -> None:
    notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
    suffix = Path(csv_name).stem if csv_name else "comparison"
    if csv_name:
        source = notebook.cells[1].source
        notebook.cells[1].source = source.replace(
            "CSV_PATH = None  # e.g. ROOT / 'data/raw/uci_portuguese.csv'",
            f"CSV_PATH = ROOT / 'data/raw/{csv_name}'",
        )
    NotebookClient(notebook, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT / f"{suffix}.ipynb")
    FIGURES.mkdir(parents=True, exist_ok=True)
    for previous in FIGURES.glob(f"{suffix}_*.png"):
        previous.unlink()
    image_count = 0
    for cell in notebook.cells:
        for result in cell.get("outputs", []):
            image = result.get("data", {}).get("image/png")
            if image:
                image_count += 1
                (FIGURES / f"{suffix}_{image_count:02d}.png").write_bytes(base64.b64decode(image))
    print(f"{suffix}: executed; {image_count} figure(s)")


if __name__ == "__main__":
    execute("01_student_data_eda.ipynb", "kaggle_synthetic.csv")
    execute("01_student_data_eda.ipynb", "uci_portuguese.csv")
    execute("02_dataset_comparison.ipynb")
