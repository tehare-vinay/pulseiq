from pathlib import Path
from datetime import datetime
import hashlib
import json

import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:
    try:
        import pandera as pa
    except ImportError:
        pa = None

# PulseIQ Task 1: repeatable ETL, conservative cleaning, validation and logs.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"
LOG_DIR = PROJECT_ROOT / "logs"
DOC_DIR = PROJECT_ROOT / "documentation"

DATASET_PREFIX = "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - "
README_SUFFIX = "readme.csv"
DUPLICATE_EXPORT_SUFFIX = "fact_payroll(1).csv"  # duplicate copy of fact_payroll.csv

for folder in (CLEAN_DIR, REJECTED_DIR, LOG_DIR, DOC_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def discover_files():
    """Use only official PulseIQ exports; ignore README and duplicate payroll export."""
    files = []
    for path in sorted(RAW_DIR.glob("*.csv")):
        name = path.name.lower()
        if not name.startswith(DATASET_PREFIX.lower()):
            continue
        if name.endswith(README_SUFFIX) or name.endswith(DUPLICATE_EXPORT_SUFFIX):
            continue
        files.append(path)
    return files


def read_csv(path):
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Unable to decode {path.name}: {last_error}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_headers(df):
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    if df.columns.duplicated().any():
        repeated = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(f"Column names collide after normalization: {repeated}")
    return df


def clean_text_and_blanks(df):
    """Trim text and standardize blank strings to missing; do not invent values."""
    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        series = df[col].map(lambda value: value.strip() if isinstance(value, str) else value)
        df[col] = series.replace(r"^\s*$", pd.NA, regex=True)
    return df


def date_columns(df):
    for col in df.columns:
        if (col == "date" or col.endswith("_date") or col.endswith("_at")
                or col in {"valid_from", "valid_to", "onboarded_on", "trained_through", "scored_at"}):
            yield col


def standardize_dates(df):
    """Parse date-like columns only when every nonblank source value parses safely."""
    df = df.copy()
    warnings = []
    for col in date_columns(df):
        original = df[col]
        nonblank = original.notna() & original.astype("string").str.strip().ne("")
        try:
            parsed = pd.to_datetime(original, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            parsed = pd.to_datetime(original, errors="coerce")
        invalid = nonblank & parsed.isna()
        if invalid.any():
            warnings.append(f"{col}: {int(invalid.sum())} nonblank value(s) could not be parsed; source values preserved")
        else:
            df[col] = parsed
    return df, warnings


def standardize_numeric_types(df):
    """Convert likely measures to numeric only if conversion loses no nonblank values."""
    df = df.copy()
    warnings = []
    measure_words = ("salary", "pay", "cost", "amount", "revenue", "profit", "expense",
                     "balance", "debit", "credit", "hours", "days", "rate", "percent",
                     "pct", "score", "count", "headcount", "story_points", "subtotal",
                     "quantity", "deduction", "allowance", "gst", "overtime", "forecast_value",
                     "lower_80", "upper_80", "band_min", "band_mid", "band_max", "quota",
                     "cycle_time", "reopened_count", "payment_terms", "working_days", "tier_number",
                     "employees_paid", "hires", "exits", "transfers_in", "transfers_out", "active_members")
    for col in df.columns:
        # Never cast identifier/key fields, dates, flags, or categorical labels to numeric.
        if (
             col.endswith("_date")
             or col.endswith("_type")
             or col in {
                 "employee_id", "manager_id", "department_id",
                 "role_id", "date_key", "year_month",
                 "normal_balance", "cost_center", "pay_type", 
                 "day_of_week", "fiscal_quarter", "gst_registration"
                 }
        ):
            continue
        if col in {"is_current", "is_active", "is_weekend", "is_holiday", "is_working_day", "is_month_end", "is_leadership", "flagged", "is_overdue_at_cutoff", "completed_on_time", "is_group", "overtime_eligible", "prorated_for_joiners", "carry_forward_allowed", "carried_in_from_prior_period"}:
            continue
        tokens = set(col.split("_"))
        numeric_fields = {"year", "month_number", "quarter", "week_of_year", "fiscal_month_number", "fiscal_quarter", "band_reference_year", "day_of_week", "band_min_annual", "band_mid_annual", "band_max_annual", "tier_number"}
        if not (tokens.intersection(measure_words) or col in numeric_fields):
            continue
        original = df[col]
        nonblank = original.notna() & original.astype("string").str.strip().ne("")
        # Dataset exports use commas as thousands separators in numeric measures.
        normalized = original.astype("string").str.replace(",", "", regex=False)
        converted = pd.to_numeric(normalized, errors="coerce")
        invalid = nonblank & converted.isna()
        if invalid.any():
            warnings.append(f"{col}: {int(invalid.sum())} value(s) not numeric; source values preserved")
        else:
            df[col] = converted
    return df, warnings


def apply_helpers(df, table_name, reference_date):
    """Add non-destructive ETL helper columns where they do not already exist."""
    df = df.copy()
  
    if table_name.endswith("dim_employee.csv") and "hire_date" in df.columns:
        date_col = "hire_date"
    else:
        possible_dates = [
            c for c in (
                "period_end_date",
                "month_end_date",
                "month_start_date",
                "date",
                "entry_date",
                "start_date",
                "invoice_date",
                "expense_date",
                "forecast_month",
                "as_of_date",
            )
            if c in df.columns
        ]
        date_col = possible_dates[0] if possible_dates else None

    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        if "etl_year" not in df.columns:
            df["etl_year"] = parsed.dt.year.astype("Int64")
        if "etl_month" not in df.columns:
            df["etl_month"] = parsed.dt.month.astype("Int64")
 
    if table_name.endswith("dim_employee.csv") and "hire_date" in df.columns:
        hire = pd.to_datetime(df["hire_date"], errors="coerce")
        if "valid_to" in df.columns:
            valid_to = pd.to_datetime(df["valid_to"], errors="coerce")
            end = valid_to.fillna(reference_date)
        else:
            end = pd.Series(reference_date, index=df.index)
        tenure = (end - hire).dt.days
        # Negative tenure is kept as NA and flagged by validation; it is not silently corrected.
        if "tenure_days" not in df.columns:
            df["tenure_days"] = tenure.where(tenure >= 0).astype("Int64")
    return df



def pandera_checks(df, table_name):
    """Validate critical Task 1 rules and return readable issues."""
    issues = []

    # Pandera must not fail silently.
    if pa is None:
        issues.append(
            "Pandera is not installed; required Pandera validation "
            "could not run. Install dependencies from requirements.txt."
        )

    # Validate date-like columns even if parsing preserved bad source values.
    for col in df.columns:
        is_date = (
            col == "date"
            or col.endswith("_date")
            or col.endswith("_at")
            or col in {
                "valid_from",
                "valid_to",
                "onboarded_on",
                "trained_through",
            }
        )

        if not is_date:
            continue

        original = df[col]
        nonblank = (
            original.notna()
            & original.astype("string").str.strip().ne("")
        )

        parsed = pd.to_datetime(
            original, errors="coerce", format="mixed"
        )
        invalid_count = int((nonblank & parsed.isna()).sum())

        if invalid_count:
            issues.append(
                f"{col}: {invalid_count} nonblank invalid date value(s)"
            )

    # Payroll amounts must not be negative.
    if table_name.endswith("fact_payroll.csv"):
        for col in ("gross_pay", "net_pay", "employer_cost"):
            if col in df.columns:
                values = pd.to_numeric(df[col], errors="coerce")
                count = int((values < 0).sum())

                if count:
                    issues.append(
                        f"{col}: {count} negative value(s)"
                    )

    # Employee history: valid_to may be blank for a current record.
    if table_name.endswith("dim_employee.csv"):
        if {"valid_from", "valid_to"}.issubset(df.columns):
            start = pd.to_datetime(df["valid_from"], errors="coerce")
            end = pd.to_datetime(df["valid_to"], errors="coerce")
            count = int(
                (start.notna() & end.notna() & (end < start)).sum()
            )

            if count:
                issues.append(
                    f"valid_to before valid_from: {count} row(s)"
                )

        if {"hire_date", "exit_date"}.issubset(df.columns):
            hire = pd.to_datetime(df["hire_date"], errors="coerce")
            exit_date = pd.to_datetime(df["exit_date"], errors="coerce")
            count = int(
                (hire.notna() & exit_date.notna()
                 & (hire > exit_date)).sum()
            )

            if count:
                issues.append(
                    f"hire_date after exit_date: {count} row(s)"
                )

    # Leave end date must not precede its start date.
    if table_name.endswith("fact_leave.csv"):
        if {"start_date", "end_date"}.issubset(df.columns):
            start = pd.to_datetime(df["start_date"], errors="coerce")
            end = pd.to_datetime(df["end_date"], errors="coerce")
            count = int(
                (start.notna() & end.notna() & (end < start)).sum()
            )

            if count:
                issues.append(
                    f"leave end_date before start_date: {count} row(s)"
                )

    # Run Pandera on critical key and payroll rules when available.
    if pa is not None:
        checks = {}

        if table_name.endswith("dim_employee.csv"):
            if "employee_key" in df.columns:
                checks["employee_key"] = pa.Column(
                    int, nullable=False, unique=True, required=True
                )

        if table_name.endswith("fact_payroll.csv"):
            if "payroll_item_id" in df.columns:
                checks["payroll_item_id"] = pa.Column(
                    str, nullable=False, unique=True, required=True
                )

            for col in ("gross_pay", "net_pay", "employer_cost"):
                if col in df.columns:
                    checks[col] = pa.Column(
                        float,
                        nullable=True,
                        checks=pa.Check.ge(0),
                        coerce=True,
                        required=False,
                    )

        try:
            if checks:
                pa.DataFrameSchema(
                    checks, strict=False, coerce=False
                ).validate(df, lazy=True)
        except Exception as exc:
            issues.append(
                "Pandera validation: "
                + str(exc).replace("\n", " | ")[:1500]
            )

    return issues


def main():
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = discover_files()
    if not files:
        raise FileNotFoundError(f"No official PulseIQ CSVs found in {RAW_DIR}")

    # Use the dataset calendar's latest date as a fixed, repeatable tenure reference.
    # README defines the fact-data cutoff as September 2026. Do not use the
    # calendar dimension's max date: it intentionally extends beyond fact data.
    reference_date = pd.Timestamp("2026-09-30")

    logs, rejected_parts, validation_rows = [], [], []
    if pa is None:
        print("WARNING: Pandera is not installed in this Python environment. Run: pip install -r requirements.txt")
    print("=" * 68)
    print("PULSEIQ ANALYTICS | TASK 1 ETL")
    print(f"Run ID: {run_id} | Started: {started}")
    print(f"Official input files: {len(files)} | Tenure reference date: {reference_date.date()}")
    print("=" * 68)

    for path in files:  
        input_rows = output_rows = duplicate_rows = 0
        warnings, validation_issues = [], []
        status, error = "FAILED", ""
        try:
            raw = read_csv(path)
            input_rows = len(raw)
            digest = sha256(path)
            df = normalize_headers(raw)
            df = clean_text_and_blanks(df)

            # Remove exact duplicates only after trimming whitespace; never deduplicate business keys blindly.
            duplicate_mask = df.duplicated(keep="first")
            duplicates = df.loc[duplicate_mask].copy()
            duplicate_rows = len(duplicates)
            df = df.loc[~duplicate_mask].copy()
            if not duplicates.empty:
                duplicates.insert(0, "_source_file", path.name)
                duplicates.insert(1, "_rejection_reason", "exact_duplicate_row")
                rejected_parts.append(duplicates)

            df, date_warnings = standardize_dates(df)
            df, numeric_warnings = standardize_numeric_types(df)
            warnings.extend(date_warnings + numeric_warnings)
            df = apply_helpers(df, path.name.lower(), reference_date)
            validation_issues = pandera_checks(df, path.name.lower())

            output_name = path.name
            df.to_csv(CLEAN_DIR / output_name, index=False, date_format="%Y-%m-%d %H:%M:%S")
            output_rows = len(df)
            status = "SUCCESS" if not validation_issues else "REVIEW"
            for issue in validation_issues:
                validation_rows.append({"run_id": run_id, "file_name": path.name, "status": "REVIEW", "issue": issue})
            print(f"[{status}] {path.name} | in={input_rows:,} out={output_rows:,} exact_duplicates={duplicate_rows:,}")
        except Exception as exc:
            error = str(exc)
            digest = ""
            print(f"[FAILED] {path.name}: {error}")

        logs.append({
            "run_id": run_id, "file_name": path.name, "started_at": started,
            "input_rows": input_rows, "output_rows": output_rows,
            "duplicate_rows": duplicate_rows, "rejected_rows": duplicate_rows,
            "source_sha256": digest if 'digest' in locals() else "",
            "status": status, "warnings": "; ".join(warnings + (["Pandera unavailable; schema checks skipped"] if pa is None else [])),
            "validation_issues": "; ".join(validation_issues), "error": error,
        })
        # Prevent a previous file's digest being accidentally reused after a failure.
        if 'digest' in locals():
            del digest

    # Stable overwrite: rejected output describes this run only, avoiding stale duplicates.
    rejected_path = REJECTED_DIR / "rejected_rows.csv"
    if rejected_parts:
        pd.concat(rejected_parts, ignore_index=True, sort=False).to_csv(rejected_path, index=False)
    else:
        pd.DataFrame(columns=["_source_file", "_rejection_reason"]).to_csv(rejected_path, index=False)

    log_path = LOG_DIR / "etl_run_log.csv"
    new_log = pd.DataFrame(logs)
    if log_path.exists():
        old_log = pd.read_csv(log_path)
        new_log = pd.concat([old_log, new_log], ignore_index=True, sort=False)
    new_log.to_csv(log_path, index=False)

    validation_path = LOG_DIR / "etl_validation_report.csv"
    pd.DataFrame(validation_rows, columns=["run_id", "file_name", "status", "issue"]).to_csv(validation_path, index=False)

    # Use the official metric dictionary; do not invent metric definitions.
    metric_files = [p for p in files if p.name.lower().endswith("metric_dictionary.csv")]
    if metric_files:
        metrics = read_csv(metric_files[0])
        metrics.head(5).to_csv(DOC_DIR / "metric_dictionary_phase1.csv", index=False)

    counts = pd.Series([r["status"] for r in logs]).value_counts().to_dict()
    print("-" * 68)
    print(f"Finished. File statuses: {counts}")
    print(f"Clean output: {CLEAN_DIR}")
    print(f"Rejected exact duplicates: {rejected_path}")
    print(f"Run history: {log_path}")
    print(f"Validation report: {validation_path}")
    print(f"Official first 5 metrics: {DOC_DIR / 'metric_dictionary_phase1.csv'}")
    print("Raw files were not modified.")

if __name__ == "__main__":
    main()
