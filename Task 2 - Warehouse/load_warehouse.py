"""Load the Task 1 clean CSV outputs into the PulseIQ PostgreSQL warehouse.

Safe to rerun: each table uses its declared primary key with ON CONFLICT DO UPDATE.
The source/raw CSV files are never changed. Extra source fields are preserved in JSONB.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = Path(os.getenv("PULSEIQ_CLEAN_DIR", str(ROOT / "data" / "clean")))
PREFIX = "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - "

# Each entry: source file suffix, target table, [(target column, source column), ...], key columns.
TABLES = [
    ("dim_department.csv", "dim_department", [
        ("department_id", "department_id"), ("department_name", "department_name")], ["department_id"]),
    ("dim_role.csv", "dim_role", [
        ("role_id", "role_id"), ("department_id", "department_id"), ("role_title", "role_title")], ["role_id"]),
    ("dim_date.csv", "dim_date", [
        ("date_key", "date_key"), ("calendar_date", "date"), ("year", "year"), ("month_number", "month_number")], ["date_key"]),
    ("dim_leave_type.csv", "dim_leave_type", [
        ("leave_type_id", "leave_type_code"), ("leave_type_name", "leave_type_name")], ["leave_type_id"]),
    ("dim_employee.csv", "dim_employee", [
        ("employee_key", "employee_key"), ("employee_id", "employee_id"), ("hire_date", "hire_date"),
        ("exit_date", "exit_date"), ("department_id", "department_id"), ("role_id", "role_id"),
        ("valid_from", "valid_from"), ("valid_to", "valid_to"), ("is_current", "is_current")], ["employee_key"]),
    ("fact_payroll.csv", "fact_payroll", [
        ("payroll_item_id", "payroll_item_id"), ("employee_id", "employee_id"), ("employee_key", "employee_key"),
        ("date_key", "date_key"), ("run_id", "run_id"), ("period_end_date", "period_end_date"),
        ("gross_pay", "gross_pay"), ("net_pay", "net_pay"), ("employer_cost", "employer_cost"),
        ("overtime_pay", "overtime_pay"), ("overtime_hours", "overtime_hours_paid")], ["payroll_item_id"]),
    ("fact_attendance_monthly.csv", "fact_attendance_monthly", [
        ("attendance_fact_id", "attendance_fact_id"), ("employee_id", "employee_id"),
        ("employee_key", "employee_key"), ("period_end_date", "period_end_date"),
        ("scheduled_days", "scheduled_days"), ("present_days", "present_days"),
        ("unpaid_absence_days", "unpaid_absence_days"), ("late_arrivals", "late_arrivals")], ["attendance_fact_id"]),
    ("fact_leave.csv", "fact_leave", [
        ("leave_request_id", "leave_request_id"), ("employee_id", "employee_id"),
        ("employee_key", "employee_key"), ("leave_type_id", "leave_type_code"),
        ("start_date", "start_date"), ("end_date", "end_date"), ("status", "status")], ["leave_request_id"]),
    ("fact_headcount_monthly.csv", "fact_headcount_monthly", [
        ("date_key", "date_key"), ("department_id", "department_id"),
        ("headcount_start", "headcount_start"), ("headcount_end", "headcount_end")], ["date_key", "department_id"]),
]

DATE_COLUMNS = {"calendar_date", "hire_date", "exit_date", "valid_from", "valid_to", "period_end_date", "start_date", "end_date"}
BOOL_COLUMNS = {"is_current"}


def find_clean_file(suffix: str) -> Path:
    matches = sorted(CLEAN_DIR.glob(f"* - {suffix}"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one clean file ending '- {suffix}' in {CLEAN_DIR}; found {len(matches)}."
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
        except ValueError:
            raise ValueError(
                f"Invalid date '{value}' in column '{target_col}'"
            )

    if target_col in BOOL_COLUMNS:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "y"}

    if target_col in {
        "employee_key", "date_key", "year", "month_number",
        "headcount_start", "headcount_end", "late_arrivals"
    }:
        return int(float(value))

    if target_col in {
        "gross_pay", "net_pay", "employer_cost", "overtime_pay",
        "overtime_hours", "scheduled_days", "present_days",
        "unpaid_absence_days", "money_at_risk", "deductions",
        "amount", "invoice_amount", "paid_amount", "outstanding_amount",
        "total_amount", "gross_amount", "net_amount", "employer_cost_amount"
    }:
        # Some source exports format numeric amounts as currency strings, e.g. "$47,844.46".
        # Remove display-only currency symbols/separators before numeric conversion.
        numeric_text = str(value).strip().replace(",", "").replace("$", "")
        if numeric_text.startswith("(") and numeric_text.endswith(")"):
            numeric_text = "-" + numeric_text[1:-1].strip()
        if numeric_text.startswith("â‚¹"):
            numeric_text = numeric_text[1:].strip()
        return float(numeric_text)

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

def load_one(conn, suffix, table, mapping, keys):
    path = find_clean_file(suffix)
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = sorted({source for _, source in mapping} - set(df.columns))
    if missing:
        raise ValueError(f"{path.name} is missing required source columns: {missing}")

    # Quarantine the known invalid leave date rows rather than violating
    # the warehouse CHECK constraint or silently losing the source records.
    if table == "fact_leave":
        start = pd.to_datetime(df["start_date"], errors="coerce")
        end = pd.to_datetime(df["end_date"], errors="coerce")
        invalid_mask = start.notna() & end.notna() & (end < start)
        rejected_dir = ROOT / "data" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        rejected_path = rejected_dir / "warehouse_fact_leave_invalid_dates.csv"
        df.loc[invalid_mask].to_csv(rejected_path, index=False)
        if invalid_mask.any():
            print(f"[QUARANTINE] fact_leave: {int(invalid_mask.sum())} rows with end_date before start_date saved to {rejected_path}")
            df = df.loc[~invalid_mask].copy()

    target_cols = [target for target, _ in mapping]
    source_cols = [source for _, source in mapping]
    extra_cols = [c for c in df.columns if c not in source_cols]
    target_cols_with_attrs = target_cols + ["attributes"]
    key_set = set(keys)
    update_cols = [c for c in target_cols if c not in key_set]
    update_cols.append("attributes")

    rows = []
    for record in df.to_dict(orient="records"):
        values = [to_python(record[source], target) for target, source in mapping]
        extras = {col: json_safe(record.get(col)) for col in extra_cols}
        rows.append(tuple(values + [json.dumps(extras, ensure_ascii=False)]))

    if not rows:
        print(f"[LOAD] {table}: source is empty; skipped")
        return 0

    columns_sql = ", ".join(target_cols_with_attrs)
    placeholders = ["%s"] * len(target_cols) + ["%s::jsonb"]
    template = "(" + ", ".join(placeholders) + ")"
    conflict_keys = ", ".join(keys)
    assignments = ", ".join(f"{col}=EXCLUDED.{col}" for col in update_cols)
    sql = (
        f"INSERT INTO warehouse.{table} ({columns_sql}) VALUES %s "
        f"ON CONFLICT ({conflict_keys}) DO UPDATE SET {assignments}"
    )

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template=template, page_size=1000)
    print(f"[LOADED] {table}: {len(rows):,} source rows (upsert key: {conflict_keys})")
    return len(rows)


def main():
    if not CLEAN_DIR.exists():
        raise FileNotFoundError(f"Clean data folder not found: {CLEAN_DIR}")

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
        # Dimension tables are loaded before facts to satisfy foreign keys.
        for spec in TABLES:
            total += load_one(conn, *spec)
        conn.commit()
        print("=" * 68)
        print(f"WAREHOUSE LOAD SUCCESSFUL | source rows processed: {total:,}")
        print("Safe to rerun: primary-key upserts prevent duplicate key inserts.")
        print("Raw files were not modified.")
        print("=" * 68)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

