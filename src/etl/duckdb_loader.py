"""Idempotently load official raw PulseIQ CSV feeds into a local DuckDB file."""
from __future__ import annotations
import json
import re
import os
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFIX = "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - "


def table_name(csv_path: Path) -> str:
    name = csv_path.name
    if name.lower().startswith(PREFIX.lower()):
        name = name[len(PREFIX):]
    result = re.sub(r"[^a-zA-Z0-9_]+", "_", Path(name).stem).strip("_").lower()
    if not result:
        raise ValueError(f"Could not derive table name from {csv_path.name}")
    return result


def load_csv_files(csv_files, db_path=None, log_dir=None):
    import duckdb
    db_path = Path(db_path or os.getenv("PULSEIQ_DUCKDB_PATH", PROJECT_ROOT / "data" / "pulseiq_task1.duckdb"))
    log_dir = Path(log_dir or PROJECT_ROOT / "logs")
    files = sorted(Path(p) for p in csv_files if Path(p).is_file() and Path(p).suffix.lower() == ".csv")
    if not files:
        raise FileNotFoundError("No eligible raw CSV feeds found in the configured raw-data directory.")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    counts = []
    con = duckdb.connect(str(db_path))
    try:
        for i, csv_path in enumerate(files):
            df = pd.read_csv(csv_path, low_memory=False)
            if df.columns.duplicated().any():
                raise ValueError(f"Duplicate columns in {csv_path.name}")
            table = table_name(csv_path)
            view = f"_task1_input_{i}"
            con.register(view, df)
            try:
                con.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM "{view}"')
            finally:
                con.unregister(view)
            actual = int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            expected = int(len(df))
            counts.append({"csv_file": csv_path.name, "table_name": table, "csv_rows": expected, "duckdb_rows": actual, "match": expected == actual})
            print(f"[DUCKDB {'OK' if actual == expected else 'MISMATCH'}] {table}: CSV={expected:,} | DuckDB={actual:,}")
    finally:
        con.close()
    summary_path = log_dir / "etl_duckdb_row_count_summary.csv"
    pd.DataFrame(counts).to_csv(summary_path, index=False)
    matches = all(row["match"] for row in counts)
    result = {"status": "SUCCESS" if matches else "FAILED", "database": str(db_path), "tables_loaded": len(counts), "rows_loaded": sum(row["duckdb_rows"] for row in counts), "row_count_summary": str(summary_path), "details": f"CSV row counts matched DuckDB for {sum(row['match'] for row in counts)}/{len(counts)} tables."}
    (log_dir / "etl_duckdb_load_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not matches:
        raise AssertionError(result["details"])
    return result


def discover_raw_files():
    raw_dir = Path(os.getenv("PULSEIQ_RAW_DIR", PROJECT_ROOT / "data" / "raw"))
    files = []
    for path in sorted(raw_dir.glob("*.csv")):
        name = path.name.lower()
        if not name.startswith(PREFIX.lower()):
            continue
        if name.endswith("readme.csv") or name.endswith("fact_payroll(1).csv"):
            continue
        files.append(path)
    return files


def main():
    result = load_csv_files(discover_raw_files())
    print("=" * 68)
    print(f"DUCKDB LOAD {result['status']} | tables={result['tables_loaded']} | rows={result['rows_loaded']:,}")
    print(f"Database: {result['database']}")
    print(f"Row-count summary: {result['row_count_summary']}")
    print("Safe to rerun: each table is replaced from its current clean CSV.")
    print("=" * 68)

if __name__ == "__main__":
    main()
