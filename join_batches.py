from __future__ import annotations

from pathlib import Path
import gc

import pandas as pd


ROOT = Path(__file__).resolve().parent
TMP_DIR = ROOT / "tmp"
OUTPUT_PATH = ROOT / "full_crm_example.csv"
XLSX_OUTPUT_PATH = ROOT / "full_crm_example.xlsx"
INTERMEDIATE_PATH = ROOT / "full_crm_no_id.tmp.csv"
CHUNK_SIZE = 1000

FULL_HEADER = [
    "ID",
    "Folder name",
    "First name",
    "Last name",
    "DOB",
    "Email",
    "Phone number",
    "Address",
    "Product",
    "Policy #",
    "Effective",
    "Expiry",
    "Carrier",
    "Premium",
    "Deductible",
    "Coverage",
    "Notes",
]

DATA_HEADER = FULL_HEADER[1:]


def iter_batch_files() -> list[Path]:
    files = sorted(TMP_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {TMP_DIR}")
    return files


def validate_header(path: Path) -> None:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    if header != FULL_HEADER:
        raise ValueError(
            f"Header mismatch in {path.name}.\n"
            f"Expected: {FULL_HEADER}\n"
            f"Found:    {header}"
        )


def remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def build_intermediate(files: list[Path]) -> None:
    remove_if_exists(INTERMEDIATE_PATH)

    wrote_header = False
    for path in files:
        validate_header(path)
        print(f"Merging {path.name} into intermediate file...")

        for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE):
            chunk = chunk[DATA_HEADER]
            chunk.to_csv(
                INTERMEDIATE_PATH,
                mode="a",
                index=False,
                header=not wrote_header,
            )
            wrote_header = True

            del chunk
            gc.collect()


def build_final_output() -> int:
    remove_if_exists(OUTPUT_PATH)

    next_id = 0
    wrote_header = False

    for chunk in pd.read_csv(INTERMEDIATE_PATH, chunksize=CHUNK_SIZE):
        row_count = len(chunk)
        chunk.insert(0, "ID", range(next_id, next_id + row_count))
        chunk.to_csv(
            OUTPUT_PATH,
            mode="a",
            index=False,
            header=not wrote_header,
        )
        wrote_header = True
        next_id += row_count

        del chunk
        gc.collect()

    return next_id


def build_xlsx_output() -> None:
    remove_if_exists(XLSX_OUTPUT_PATH)

    with pd.ExcelWriter(XLSX_OUTPUT_PATH, engine="openpyxl") as writer:
        start_row = 0
        wrote_header = False

        for chunk in pd.read_csv(OUTPUT_PATH, chunksize=CHUNK_SIZE):
            chunk.to_excel(
                writer,
                sheet_name="full_crm",
                index=False,
                header=not wrote_header,
                startrow=start_row,
            )

            start_row += len(chunk) + (0 if wrote_header else 1)
            wrote_header = True

            del chunk
            gc.collect()


def main() -> None:
    files = iter_batch_files()
    print(f"Found {len(files)} batch files in {TMP_DIR}")

    try:
        build_intermediate(files)
        total_rows = build_final_output()
        build_xlsx_output()
    finally:
        remove_if_exists(INTERMEDIATE_PATH)

    print(f"Wrote {OUTPUT_PATH.name}")
    print(f"Wrote {XLSX_OUTPUT_PATH.name}")
    print(f"Final row count: {total_rows}")


if __name__ == "__main__":
    main()
