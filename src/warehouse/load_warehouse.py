"""
Load the Task 1 clean CSV outputs into the PulseIQ PostgreSQL warehouse.

Safe to rerun: each table uses its declared primary key with
ON CONFLICT DO UPDATE.

Invalid leave-date rows are quarantined before loading.
The source/raw CSV files are never changed.
Extra source fields are preserved in JSONB.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = Path(
    os.getenv("PULSEIQ_CLEAN_DIR", str(ROOT / "data" / "clean"))
)
PREFIX = "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - "


# Each entry:
# (source file suffix, target table, [(target column, source column), ...], key columns)
TABLES = [
    (
        "dim_department.csv",
        "dim_department",
        [
            ("department_id", "department_id"),
            ("department_name", "department_name"),
        ],
        ["department_id"],
    ),
    (
        "dim_role.csv",
        "dim_role",
        [
            ("role_id", "role_id"),
            ("department_id", "department_id"),
            ("role_title", "role_title"),
        ],
        ["role_id"],
    ),
    (
        "dim_date.csv",
        "dim_date",
        [
            ("date_key", "date_key"),
            ("calendar_date", "date"),
            ("year", "year"),
            ("month_number", "month_number"),
        ],
        ["date_key"],
    ),
    (
        "dim_leave_type.csv",
        "dim_leave_type",
        [
            ("leave_type_id", "leave_type_code"),
            ("leave_type_name", "leave_type_name"),
        ],
        ["leave_type_id"],
    ),
    (
        "dim_employee.csv",
        "dim_employee",
        [
            ("employee_key", "employee_key"),
            ("employee_id", "employee_id"),
            ("hire_date", "hire_date"),
            ("exit_date", "exit_date"),
            ("department_id", "department_id"),
            ("role_id", "role_id"),
            ("valid_from", "valid_from"),
            ("valid_to", "valid_to"),
            ("is_current", "is_current"),
        ],
        ["employee_key"],
    ),
    (
        "fact_payroll.csv",
        "fact_payroll",
        [
            ("payroll_item_id", "payroll_item_id"),
            ("employee_id", "employee_id"),
            ("employee_key", "employee_key"),
            ("date_key", "date_key"),
            ("run_id", "run_id"),
            ("period_end_date", "period_end_date"),
            ("gross_pay", "gross_pay"),
            ("net_pay", "net_pay"),
            ("employer_cost", "employer_cost"),
            ("overtime_pay", "overtime_pay"),
            ("overtime_hours", "overtime_hours_paid"),
        ],
        ["payroll_item_id"],
    ),
    (
        "fact_attendance_monthly.csv",
        "fact_attendance_monthly",
        [
            ("attendance_fact_id", "attendance_fact_id"),
            ("employee_id", "employee_id"),
            ("employee_key", "employee_key"),
            ("period_end_date", "period_end_date"),
            ("scheduled_days", "scheduled_days"),
            ("present_days", "present_days"),
            ("unpaid_absence_days", "unpaid_absence_days"),
            ("late_arrivals", "late_arrivals"),
        ],
        ["attendance_fact_id"],
    ),
    (
        "fact_leave.csv",
        "fact_leave",
        [
            ("leave_request_id", "leave_request_id"),
            ("employee_id", "employee_id"),
            ("employee_key", "employee_key"),
            ("leave_type_id", "leave_type_code"),
            ("start_date", "start_date"),
            ("end_date", "end_date"),
            ("status", "status"),
        ],
        ["leave_request_id"],
    ),
    (
        "fact_headcount_monthly.csv",
        "fact_headcount_monthly",
        [
            ("date_key", "date_key"),
            ("department_id", "department_id"),
            ("headcount_start", "headcount_start"),
            ("headcount_end", "headcount_end"),
        ],
        ["date_key", "department_id"],
    ),
]


DATE_COLUMNS = {
    "calendar_date",
    "hire_date",
    "exit_date",
    "valid_from",
    "valid_to",
    "period_end_date",
    "start_date",
    "end_date",
}

BOOL_COLUMNS = {"is_current"}


def find_clean_file(suffix: str) -> Path:
    matches = sorted(CLEAN_DIR.glob(f"* - {suffix}"))

    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one clean file ending '- {suffix}' "
            f"in {CLEAN_DIR}; found {len(matches)}."
        )

    return matches[0]


def blank_to_none(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def to_python(value, target_col):
    value = blank_to_none(value)

    if value is None:
        return None

    if target_col in DATE_COLUMNS:
        if isinstance(value, (pd.Timestamp, datetime, date)):
            if isinstance(value, (pd.Timestamp, datetime)):
                return value.date()
            return value

        date_text = str(value).strip()

        if date_text.startswith("9999-12-31"):
            return date(9999, 12, 31)

        try:
            return date.fromisoformat(date_text[:10])
        except ValueError as exc:
            raise ValueError(
                f"Invalid date '{value}' in column '{target_col}'"
            ) from exc

    if target_col in BOOL_COLUMNS:
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    if target_col in {
        "employee_key",
        "date_key",
        "year",
        "month_number",
        "headcount_start",
        "headcount_end",
        "late_arrivals",
    }:
        return int(float(value))

    if target_col in {
        "gross_pay",
        "net_pay",
        "employer_cost",
        "overtime_pay",
        "overtime_hours",
        "scheduled_days",
        "present_days",
        "unpaid_absence_days",
    }:
        return float(value)

    return str(value) if not isinstance(value, (int, float)) else value


def json_safe(value):
    value = blank_to_none(value)

    if value is None:
        return None

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if hasattr(value, "item"):
        return value.item()

    return value


def quarantine_invalid_leave_rows(df, source_path):
    """
    Remove leave rows with missing/unparseable dates or end_date
    earlier than start_date.

    Invalid rows are saved in a separate warehouse quarantine file.
    Previously quarantined rows are preserved and exact duplicate
    quarantine records are removed.
    """
    start = pd.to_datetime(df["start_date"], errors="coerce")
    end = pd.to_datetime(df["end_date"], errors="coerce")

    missing_start = start.isna()
    missing_end = end.isna()
    reversed_dates = start.notna() & end.notna() & (end < start)

    invalid_mask = missing_start | missing_end | reversed_dates

    rejected_dir = ROOT / "data" / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    rejected_path = (
        rejected_dir / "warehouse_fact_leave_invalid_dates.csv"
    )

    if invalid_mask.any():
        invalid_rows = df.loc[invalid_mask].copy()

        reasons = []
        for idx in invalid_rows.index:
            row_reasons = []

            if missing_start.loc[idx]:
                row_reasons.append("missing_or_invalid_start_date")

            if missing_end.loc[idx]:
                row_reasons.append("missing_or_invalid_end_date")

            if reversed_dates.loc[idx]:
                row_reasons.append("end_date_before_start_date")

            reasons.append(";".join(row_reasons))

        invalid_rows.insert(0, "_source_file", source_path.name)
        invalid_rows.insert(1, "_rejection_reason", reasons)

        if rejected_path.exists():
            previous_rows = pd.read_csv(
                rejected_path,
                dtype=str,
                low_memory=False,
            )

            combined = pd.concat(
                [previous_rows, invalid_rows],
                ignore_index=True,
                sort=False,
            )

            combined = combined.drop_duplicates()
        else:
            combined = invalid_rows

        combined.to_csv(rejected_path, index=False)

        print(
            f"[QUARANTINE] fact_leave: {len(invalid_rows)} "
            f"invalid rows recorded in {rejected_path}"
        )
    else:
        print("[QUARANTINE] fact_leave: no invalid date rows found")

    valid_df = df.loc[~invalid_mask].copy()

    return valid_df


def load_one(conn, suffix, table, mapping, keys):
    path = find_clean_file(suffix)

    df = pd.read_csv(path, dtype=str, low_memory=False)
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = sorted(
        {source for _, source in mapping} - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"{path.name} is missing required source columns: {missing}"
        )

    # Quarantine invalid leave-date records before warehouse insertion.
    if table == "fact_leave":
        df = quarantine_invalid_leave_rows(df, path)

    target_cols = [target for target, _ in mapping]
    source_cols = [source for _, source in mapping]

    extra_cols = [col for col in df.columns if col not in source_cols]

    target_cols_with_attrs = target_cols + ["attributes"]

    key_set = set(keys)
    update_cols = [
        col for col in target_cols if col not in key_set
    ]
    update_cols.append("attributes")

    rows = []

    for record in df.to_dict(orient="records"):
        values = [
            to_python(record[source], target)
            for target, source in mapping
        ]

        extras = {
            col: json_safe(record.get(col))
            for col in extra_cols
        }

        rows.append(
            tuple(values + [json.dumps(extras, ensure_ascii=False)])
        )

    if not rows:
        print(f"[LOAD] {table}: no valid source rows; skipped")
        return 0

    columns_sql = ", ".join(target_cols_with_attrs)
    placeholders = ["%s"] * len(target_cols) + ["%s::jsonb"]
    template = "(" + ", ".join(placeholders) + ")"

    conflict_keys = ", ".join(keys)

    assignments = ", ".join(
        f"{col}=EXCLUDED.{col}" for col in update_cols
    )

    sql = (
        f"INSERT INTO warehouse.{table} ({columns_sql}) VALUES %s "
        f"ON CONFLICT ({conflict_keys}) DO UPDATE SET {assignments}"
    )

    with conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            rows,
            template=template,
            page_size=1000,
        )

    print(
        f"[LOADED] {table}: {len(rows):,} valid source rows "
        f"(upsert key: {conflict_keys})"
    )

    return len(rows)


def main():
    if not CLEAN_DIR.exists():
        raise FileNotFoundError(
            f"Clean data folder not found: {CLEAN_DIR}"
        )

    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "postgres"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "pulseiq_warehouse"),
        user=os.getenv("POSTGRES_USER", "pulseiq_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pulseiq_local_dev"),
        connect_timeout=15,
    )

    conn.autocommit = False
    total = 0

    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO warehouse, public;")

        # Load dimensions before facts to satisfy foreign-key constraints.
        for spec in TABLES:
            total += load_one(conn, *spec)

        conn.commit()

        print("=" * 68)
        print(
            f"WAREHOUSE LOAD SUCCESSFUL | "
            f"valid source rows processed: {total:,}"
        )
        print(
            "Safe to rerun: primary-key upserts prevent duplicate "
            "key inserts."
        )
        print(
            "Invalid leave-date rows, if any, were quarantined."
        )
        print("Raw files were not modified.")
        print("=" * 68)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()