
from pathlib import Path
import hashlib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def file_hash(path):
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def read_csv(path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                low_memory=False
            )
        except UnicodeDecodeError:
            continue

    raise ValueError("Unsupported CSV encoding")


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in: {RAW_DIR}")
        return

    summary = []
    column_details = []
    hashes = {}

    print(f"Raw folder: {RAW_DIR}")
    print(f"CSV files found: {len(files)}\n")

    for path in files:
        print(f"Reading: {path.name}")

        try:
            df = read_csv(path)
            digest = file_hash(path)

            hashes.setdefault(digest, []).append(path.name)

            summary.append({
                "file_name": path.name,
                "rows": len(df),
                "columns": len(df.columns),
                "duplicate_full_rows": int(df.duplicated().sum()),
                "missing_cells": int(df.isna().sum().sum()),
                "status": "SUCCESS",
                "error": ""
            })

            for col in df.columns:
                column_details.append({
                    "file_name": path.name,
                    "column_name": col,
                    "data_type": str(df[col].dtype),
                    "missing_count": int(df[col].isna().sum()),
                    "distinct_values": int(df[col].nunique())
                })

            print(
                f"  Rows: {len(df):,} | "
                f"Columns: {len(df.columns)} | "
                f"Duplicate rows: {df.duplicated().sum():,}"
            )

        except Exception as exc:
            summary.append({
                "file_name": path.name,
                "rows": None,
                "columns": None,
                "duplicate_full_rows": None,
                "missing_cells": None,
                "status": "FAILED",
                "error": str(exc)
            })

            print(f"  ERROR: {exc}")

    pd.DataFrame(summary).to_csv(
        LOG_DIR / "data_profile_summary.csv",
        index=False
    )

    pd.DataFrame(column_details).to_csv(
        LOG_DIR / "data_profile_columns.csv",
        index=False
    )

    print("\n--- PROFILE COMPLETE ---")
    print(f"Summary: {LOG_DIR / 'data_profile_summary.csv'}")
    print(f"Columns: {LOG_DIR / 'data_profile_columns.csv'}")

    duplicate_groups = [
        names for names in hashes.values() if len(names) > 1
    ]

    if duplicate_groups:
        print("\nFiles with identical content:")
        for names in duplicate_groups:
            print("  " + " == ".join(names))
    else:
        print("\nNo byte-identical CSV files found.")

    failed = sum(item["status"] == "FAILED" for item in summary)
    print(f"Successful files: {len(summary) - failed}")
    print(f"Failed files: {failed}")


if __name__ == "__main__":
    main()
