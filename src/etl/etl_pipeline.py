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
def find_project_root(script_path):
    for candidate in [script_path.parent, *script_path.parents]:
        if (candidate / "data" / "raw").is_dir():
            return candidate
        if (candidate / "Clean Data").is_dir() and (candidate / "Task 1 - ETL").is_dir():
            return candidate
    return script_path.resolve().parent

PROJECT_ROOT = find_project_root(Path(__file__).resolve())
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
    """Use official raw exports; selected-file ZIP fallback supports package validation."""
    source_dir = RAW_DIR
    if not source_dir.is_dir() or not list(source_dir.glob("*.csv")):
        source_dir = PROJECT_ROOT / "Clean Data"
    files = []
    for path in sorted(source_dir.glob("*.csv")):
        name = path.name.lower()
        if not name.startswith(DATASET_PREFIX.lower()):
            continue
        if name.endswith(README_SUFFIX) or name.endswith(DUPLICATE_EXPORT_SUFFIX):
            continue
        files.append(path)
    return files


def find_contract_file(files):
    for path in files:
        if path.name.lower().endswith("data_contracts.csv"):
            return path
    for folder in (RAW_DIR, PROJECT_ROOT / "Clean Data", PROJECT_ROOT / "data" / "contracts"):
        if folder.exists():
            matches = list(folder.glob("*data_contracts.csv"))
            if len(matches) == 1:
                return matches[0]
    return None


def contract_table_name(feed):
    import re
    match = re.search(r"\(([^()]+)\)\s*$", str(feed))
    return match.group(1).strip().lower() + ".csv" if match else None


def validate_contract(df, filename, contracts):
    """Check required contract columns and nullable=no rules where contract rows exist."""
    if contracts is None or contracts.empty:
        return ["Official data contract missing or empty"]
    rules = contracts.copy()
    rules.columns = [str(c).strip().lower() for c in rules.columns]
    rules["_table"] = rules["feed"].map(contract_table_name)
    matched = rules[rules["_table"] == filename.lower()]
    if matched.empty:
        return []  # The contract file covers only explicitly listed feeds.
    issues = []
    expected = set(matched["column_name"].astype(str).str.strip().str.lower())
    actual = set(map(str.lower, df.columns))
    missing = sorted(expected - actual)
    if missing:
        issues.append("Missing contract columns: " + ", ".join(missing))
    unexpected = sorted(actual - expected)
    if unexpected:
        issues.append(
            "Unexpected columns (preserved; contract review required): "
            + ", ".join(unexpected)
        )
    for _, rule in matched.iterrows():
        col = str(rule["column_name"]).strip().lower()
        nullable = str(rule.get("nullable", "yes")).strip().lower() in {"yes", "y", "true", "1"}
        if col in df.columns and not nullable:
            blank = df[col].isna() | df[col].astype("string").str.strip().eq("")
            count = int(blank.sum())
            if count:
                issues.append(f"{col}: {count} row(s) violate nullable=no")
    return issues


def write_contract_notes(contracts):
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    if contracts is None or contracts.empty:
        body = "Contract file was not found; column-level contract validation could not run."
    else:
        feeds = contracts["feed"].dropna().drop_duplicates().astype(str).tolist()
        body = (f"Contract rows: {len(contracts)}\nContract feeds: {len(feeds)}\n\n" +
                "Covered feeds:\n" + "\n".join(f"- {x}" for x in feeds) +
                "\n\nCoverage note: only feeds explicitly present in data_contracts.csv receive column-level contract checks. Other tables still receive ETL business-rule checks and should have contract rows added in a future contract revision.\n")
    (DOC_DIR / "task1_data_contract_notes.md").write_text(
        "# Task 1 — Data contract notes\n\nSource: official PulseIQ data_contracts.csv.\n\n" + body +
        "\n\nRaw source files are read-only. Exact duplicate rows are quarantined with a written reason; repeated business keys are not automatically removed.\n",
        encoding="utf-8")


def load_postgres_idempotently(clean_files):
    """Transactional truncate/reload into TEXT staging tables; reruns do not append duplicates."""
    import os, re
    required = ["PULSEIQ_PGDATABASE", "PULSEIQ_PGUSER", "PULSEIQ_PGPASSWORD"]
    if not all(os.getenv(k) for k in required):
        return {"status": "SKIPPED", "details": "Set PULSEIQ_PGDATABASE, PULSEIQ_PGUSER and PULSEIQ_PGPASSWORD; database load not claimed."}
    try:
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extras import execute_batch
        conn = psycopg2.connect(host=os.getenv("PULSEIQ_PGHOST", "localhost"), port=int(os.getenv("PULSEIQ_PGPORT", "5432")), dbname=os.environ["PULSEIQ_PGDATABASE"], user=os.environ["PULSEIQ_PGUSER"], password=os.environ["PULSEIQ_PGPASSWORD"])
        loaded = []
        try:
            with conn:
                with conn.cursor() as cur:
                    for csv_path in clean_files:
                        df = pd.read_csv(csv_path, low_memory=False)
                        name = csv_path.name
                        if name.lower().startswith(DATASET_PREFIX.lower()): name = name[len(DATASET_PREFIX):]
                        table = re.sub(r"[^a-z0-9_]+", "_", Path(name).stem.lower()).strip("_")
                        columns = [re.sub(r"[^a-zA-Z0-9_]+", "_", str(c)).strip("_").lower() for c in df.columns]
                        if len(columns) != len(set(columns)): raise ValueError(f"SQL column-name collision in {csv_path.name}")
                        cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(sql.Identifier(table), sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in columns)))
                        cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table)))
                        if columns and len(df):
                            q = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)), sql.SQL(", ").join(sql.Placeholder() for _ in columns))
                            rows = [tuple(None if pd.isna(v) else str(v) for v in row) for row in df.itertuples(index=False, name=None)]
                            execute_batch(cur, q.as_string(conn), rows, page_size=1000)
                        loaded.append({"table": table, "rows": len(df)})
        finally: conn.close()
        return {"status": "SUCCESS", "details": json.dumps(loaded)}
    except Exception as exc:
        return {"status": "FAILED", "details": f"{type(exc).__name__}: {exc}"}


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
            parsed = pd.to_datetime(original, errors="coerce", format="mixed")
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
        invalid_mask = nonblank & parsed.isna()
        if col == "valid_to":
            open_ended = original.astype("string").str.strip().str.startswith("9999-12-31", na=False)
            invalid_mask &= ~open_ended
        invalid_count = int(invalid_mask.sum())

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
    """Run the Task 1 ETL with repeatable cleaning, quarantine, validation and logs."""
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = discover_files()
    if not files:
        raise FileNotFoundError(f"No official PulseIQ CSVs found in {RAW_DIR}")

    contract_path = find_contract_file(files)
    contracts = read_csv(contract_path) if contract_path else None
    if contracts is not None:
        contracts.columns = [str(column).strip().lower() for column in contracts.columns]
    write_contract_notes(contracts)

    # Fixed end-of-period reference makes tenure calculations repeatable.
    reference_date = pd.Timestamp("2026-09-30")
    logs = []
    rejected_parts = []
    validation_rows = []

    if pa is None:
        print("WARNING: Pandera is not installed; install project requirements to enable schema checks.")

    print("=" * 68)
    print("PULSEIQ ANALYTICS | TASK 1 ETL")
    print(f"Run ID: {run_id} | Started: {started}")
    print(f"Official input files: {len(files)} | Tenure reference date: {reference_date.date()}")
    print("=" * 68)

    for path in files:
        input_rows = 0
        output_rows = 0
        duplicate_rows = 0
        quarantined_rows = 0
        warnings = []
        validation_issues = []
        status = "FAILED"
        error = ""
        digest = ""

        try:
            raw = read_csv(path)
            input_rows = len(raw)
            digest = sha256(path)
            df = normalize_headers(raw)
            df = clean_text_and_blanks(df)

            # Remove exact duplicate rows only; do not deduplicate business keys.
            duplicate_mask = df.duplicated(keep="first")
            duplicates = df.loc[duplicate_mask].copy()
            duplicate_rows = len(duplicates)
            df = df.loc[~duplicate_mask].copy()
            if not duplicates.empty:
                duplicates.insert(0, "_source_file", path.name)
                duplicates.insert(1, "_rejection_reason", "exact_duplicate_row")
                rejected_parts.append(duplicates)

            df, date_warnings = standardize_dates(df)
            warnings.extend(date_warnings)

            # Invalid leave date ranges are quarantined, never silently swapped/deleted.
            if path.name.lower().endswith("fact_leave.csv"):
                if {"start_date", "end_date"}.issubset(df.columns):
                    start_dates = pd.to_datetime(df["start_date"], errors="coerce")
                    end_dates = pd.to_datetime(df["end_date"], errors="coerce")
                    invalid_mask = (
                        start_dates.notna()
                        & end_dates.notna()
                        & (end_dates < start_dates)
                    )
                    invalid_leaves = df.loc[invalid_mask].copy()
                    quarantined_rows = len(invalid_leaves)

                    if not invalid_leaves.empty:
                        invalid_leaves.insert(0, "_source_file", path.name)
                        invalid_leaves.insert(
                            1,
                            "_rejection_reason",
                            "leave_end_date_before_start_date",
                        )
                        rejected_parts.append(invalid_leaves)
                        # Save invalid leave rows with their rejection reason.
                        invalid_leave_path = REJECTED_DIR / "warehouse_fact_leave_invalid_dates.csv"
                        invalid_leaves.to_csv(invalid_leave_path, index=False)
                        df = df.loc[~invalid_mask].copy()
                else:
                    validation_issues.append(
                        "Required columns start_date/end_date are missing; leave-date rule not checked"
                    )

            df, numeric_warnings = standardize_numeric_types(df)
            warnings.extend(numeric_warnings)
            df = apply_helpers(df, path.name.lower(), reference_date)

            validation_issues.extend(pandera_checks(df, path.name.lower()))
            validation_issues.extend(validate_contract(df, path.name, contracts))

            if quarantined_rows:
                validation_issues.append(
                    f"{quarantined_rows} invalid leave-date row(s) quarantined; source records require business review"
                )

            # Always write the cleaned output, even when its status is REVIEW.
            output_path = CLEAN_DIR / path.name
            df.to_csv(
                output_path,
                index=False,
                date_format="%Y-%m-%d %H:%M:%S",
            )
            output_rows = len(df)
            status = "SUCCESS" if not validation_issues else "REVIEW"

            for issue in validation_issues:
                validation_rows.append(
                    {
                        "run_id": run_id,
                        "file_name": path.name,
                        "status": "REVIEW",
                        "issue": issue,
                    }
                )

            print(
                f"[{status}] {path.name} | in={input_rows:,} out={output_rows:,} "
                f"exact_duplicates={duplicate_rows:,} quarantined={quarantined_rows:,}"
            )

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            status = "FAILED"
            print(f"[FAILED] {path.name}: {error}")

        rows_quarantined_total = duplicate_rows + quarantined_rows
        rows_passed = output_rows

        logs.append(
            {
                "run_id": run_id,
                "file_name": path.name,
                "started_at": started,
                "input_rows": input_rows,
                "output_rows": output_rows,
                "rows_passed": rows_passed,
                "duplicate_rows": duplicate_rows,
                "invalid_leave_rows_quarantined": quarantined_rows,
                "rows_quarantined": rows_quarantined_total,
                "quarantined_rows": quarantined_rows,
                "rejected_rows": rows_quarantined_total,
                "source_sha256": digest,
                "status": status,
                "warnings": "; ".join(warnings),
                "validation_issues": "; ".join(validation_issues),
                "error": error,
            }
        )

    # rejected_rows.csv describes this run only; run history remains append-only.
    rejected_path = REJECTED_DIR / "rejected_rows.csv"
    if rejected_parts:
        pd.concat(rejected_parts, ignore_index=True, sort=False).to_csv(
            rejected_path, index=False
        )
    else:
        pd.DataFrame(
            columns=["_source_file", "_rejection_reason"]
        ).to_csv(rejected_path, index=False)

    log_path = LOG_DIR / "etl_run_log.csv"
    new_log = pd.DataFrame(logs)
    if log_path.exists():
        try:
            old_log = pd.read_csv(log_path)
            new_log = pd.concat([old_log, new_log], ignore_index=True, sort=False)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError):
            # Do not block this run if an older log is malformed; retain current run log.
            pass
    new_log.to_csv(log_path, index=False)

    validation_path = LOG_DIR / "etl_validation_report.csv"
    pd.DataFrame(
        validation_rows,
        columns=["run_id", "file_name", "status", "issue"],
    ).to_csv(validation_path, index=False)

    summary_path = LOG_DIR / "etl_row_count_summary.csv"
    pd.DataFrame(logs)[
        [
            "run_id", "file_name", "input_rows", "rows_passed", "rows_quarantined",
            "output_rows", "duplicate_rows", "invalid_leave_rows_quarantined",
            "quarantined_rows", "rejected_rows", "status",
        ]
    ].to_csv(summary_path, index=False)

    # Database load status is explicit; missing credentials mean SKIPPED, not success.
    db_result = load_postgres_idempotently(sorted(CLEAN_DIR.glob("*.csv")))
    database_report = {"run_id": run_id, **db_result}
    (LOG_DIR / "etl_database_load_report.json").write_text(
        json.dumps(database_report, indent=2), encoding="utf-8"
    )

    # Task 1 requires a local, single-file DuckDB database in addition to the existing PostgreSQL workflow.
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src" / "etl"))
        from duckdb_loader import load_csv_files
        duckdb_result = load_csv_files(
            files,
            PROJECT_ROOT / "data" / "pulseiq_task1.duckdb",
            LOG_DIR,
        )
    except Exception as exc:
        duckdb_result = {"status": "FAILED", "database": str(PROJECT_ROOT / "data" / "pulseiq_task1.duckdb"), "details": f"{type(exc).__name__}: {exc}", "tables_loaded": 0, "rows_loaded": 0}
    (LOG_DIR / "etl_duckdb_load_report.json").write_text(
        json.dumps({"run_id": run_id, **duckdb_result}, indent=2), encoding="utf-8"
    )

    metric_files = [
        path for path in files
        if path.name.lower().endswith("metric_dictionary.csv")
    ]
    if metric_files:
        metrics = read_csv(metric_files[0])
        metrics.head(5).to_csv(DOC_DIR / "metric_dictionary_phase1.csv", index=False)

    counts = pd.Series([row["status"] for row in logs]).value_counts().to_dict()
    print("-" * 68)
    print(f"Finished. File statuses: {counts}")
    print(f"Clean output: {CLEAN_DIR}")
    print(f"Rejected rows: {rejected_path}")
    print(f"Run history: {log_path}")
    print(f"Validation report: {validation_path}")
    print(f"Row-count summary: {summary_path}")
    print(f"Contract notes: {DOC_DIR / 'task1_data_contract_notes.md'}")
    print(f"PostgreSQL load: {db_result['status']} — {db_result['details']}")
    print(f"DuckDB load: {duckdb_result['status']} — {duckdb_result.get('details', '')}")
    print("Raw source files were not modified.")


if __name__ == "__main__":
    main()
