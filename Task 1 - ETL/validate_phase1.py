
from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================================
# PULSEIQ ANALYTICS - PHASE 1 DATA VALIDATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

results = []

# Validate cleaned files first. If a cleaned file is unavailable,
# fall back to the original raw file.
PREFERRED_DIRS = [CLEAN_DIR, RAW_DIR]

# Known sentinel keys are reported for review, never silently fixed.
SENTINEL_KEYS = {"-1", "-1.0", "UNKNOWN", "N/A", "NA"}


# ============================================================
# FILE UTILITIES
# ============================================================

def find_csv(expected_name):
    """Find a CSV by its ending filename, including dataset prefixes."""
    for folder in PREFERRED_DIRS:
        if not folder.exists():
            continue

        matches = [
            path for path in folder.glob("*.csv")
            if path.name.lower().endswith(expected_name.lower())
        ]

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple matches for {expected_name} in {folder}: "
                f"{[p.name for p in matches]}"
            )

    raise FileNotFoundError(
        f"Could not find {expected_name} in data/clean or data/raw."
    )


def read_csv(path):
    """Read CSV using common encodings."""
    last_error = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(
        f"Could not decode {path.name}: {last_error}"
    )


def load_csv(expected_name):
    path = find_csv(expected_name)
    df = read_csv(path)

    # Standardize header whitespace only; preserve column meanings.
    df.columns = [str(col).strip() for col in df.columns]

    print(f"\nLoaded: {path.name}")
    print(f"Source: {path.parent}")
    print(f"Rows: {len(df):,} | Columns: {len(df.columns)}")

    return df


def normalized_keys(series):
    """Normalize key values for reliable comparisons."""
    return series.astype("string").str.strip()


# ============================================================
# REPORTING UTILITIES
# ============================================================

def record_check(check_name, dataset, status, details):
    results.append({
        "checked_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "check_name": check_name,
        "dataset": dataset,
        "status": status,
        "details": details
    })

    print(f"[{status}] {dataset} | {check_name}: {details}")


def check_required_columns(df, dataset, required_columns):
    missing = sorted(set(required_columns) - set(df.columns))

    if missing:
        record_check(
            "required_columns",
            dataset,
            "FAIL",
            f"Missing columns: {missing}"
        )
    else:
        record_check(
            "required_columns",
            dataset,
            "PASS",
            "All required columns exist."
        )


def check_unique_key(df, dataset, key):
    if key not in df.columns:
        record_check(
            "unique_key", dataset, "SKIP",
            f"Column '{key}' not found."
        )
        return

    values = normalized_keys(df[key])
    missing_mask = values.isna() | values.eq("")
    duplicate_mask = values.duplicated(keep=False) & ~missing_mask

    duplicate_count = int(duplicate_mask.sum())
    missing_count = int(missing_mask.sum())

    status = (
        "PASS"
        if duplicate_count == 0 and missing_count == 0
        else "FAIL"
    )

    record_check(
        "unique_key",
        dataset,
        status,
        f"Key={key}; duplicate rows={duplicate_count}; "
        f"missing values={missing_count}"
    )


def check_foreign_key(
    fact,
    dimension,
    fact_name,
    dimension_name,
    key,
    record_id_columns=None
):
    """
    Check fact-to-dimension key references.

    Orphans are reported, not deleted or automatically repaired.
    Sentinel keys such as -1 are explicitly identified for review.
    """
    if key not in fact.columns or key not in dimension.columns:
        record_check(
            "foreign_key",
            fact_name,
            "SKIP",
            f"Column '{key}' missing from fact or dimension."
        )
        return

    fact_keys = normalized_keys(fact[key])
    dimension_keys = set(
        normalized_keys(dimension[key]).dropna()
    )

    missing_mask = fact_keys.isna() | fact_keys.eq("")
    orphan_mask = ~missing_mask & ~fact_keys.isin(dimension_keys)

    orphan_count = int(orphan_mask.sum())
    missing_count = int(missing_mask.sum())

    orphan_values = set(fact_keys[orphan_mask].dropna())
    sentinel_values = orphan_values.intersection(SENTINEL_KEYS)

    # Show the specific affected rows to make investigation easier.
    affected_columns = [
        col for col in (record_id_columns or [])
        if col in fact.columns
    ]
    if key not in affected_columns:
        affected_columns.append(key)

    affected = fact.loc[
        orphan_mask | missing_mask, affected_columns
    ].head(10)

    sample = (
        affected.to_dict(orient="records")
        if not affected.empty else []
    )

    if orphan_count == 0 and missing_count == 0:
        status = "PASS"
        details = (
            f"{key} references valid records in {dimension_name}; "
            "no orphan or missing keys."
        )
    else:
        status = "REVIEW"

        details = (
            f"{key} against {dimension_name}; "
            f"orphan rows={orphan_count}; "
            f"missing keys={missing_count}; "
            f"sentinel orphan values={sorted(sentinel_values)}; "
            f"sample affected records={sample}"
        )

        if sentinel_values:
            details += (
                " | Sentinel keys such as -1 are placeholders "
                "and require separate investigation; "
                "they are not automatically repaired or deleted."
            )

    record_check(
        "foreign_key",
        fact_name,
        status,
        details
    )


# ============================================================
# EMPLOYEE HISTORY VALIDATION
# ============================================================

def check_employee_history(employee):
    required = {"valid_from", "valid_to"}

    if not required.issubset(employee.columns):
        record_check(
            "employee_history_dates",
            "dim_employee",
            "SKIP",
            "valid_from or valid_to column is missing."
        )
        return

    start = pd.to_datetime(
        employee["valid_from"], errors="coerce", format="mixed"
    )
    end = pd.to_datetime(
        employee["valid_to"], errors="coerce", format="mixed"
    )

    # A null valid_to can represent a currently active history version.
    invalid_start = start.isna()
    invalid_interval = end.notna() & start.notna() & (end < start)

    invalid_count = int(
        (invalid_start | invalid_interval).sum()
    )

    record_check(
        "employee_history_dates",
        "dim_employee",
        "PASS" if invalid_count == 0 else "REVIEW",
        f"Missing/invalid valid_from or valid_to before valid_from: "
        f"{invalid_count} rows. Null valid_to is allowed."
    )


# ============================================================
# MAIN VALIDATION
# ============================================================

def main():
    print("=" * 72)
    print("PULSEIQ PHASE 1 - INITIAL DATA VALIDATION")
    print("=" * 72)

    datasets = {}

    specifications = {
        "dim_employee": (
            "dim_employee.csv",
            [
                "employee_key", "employee_id", "hire_date",
                "department_id", "role_id",
                "valid_from", "valid_to", "is_current"
            ]
        ),
        "dim_department": (
            "dim_department.csv",
            ["department_id", "department_name"]
        ),
        "dim_role": (
            "dim_role.csv",
            ["role_id", "department_id", "role_title"]
        ),
        "dim_date": (
            "dim_date.csv",
            ["date_key", "year", "month_number"]
        ),
        "fact_payroll": (
            "fact_payroll.csv",
            [
                "payroll_item_id", "employee_id", "employee_key",
                "date_key", "period_end_date", "gross_pay", "net_pay"
            ]
        ),
        "fact_attendance_monthly": (
            "fact_attendance_monthly.csv",
            [
                "attendance_fact_id", "employee_id", "employee_key",
                "scheduled_days", "present_days",
                "unpaid_absence_days", "late_arrivals", "period_end_date"
            ]
        ),
        "fact_leave": (
            "fact_leave.csv",
            [
                "leave_request_id", "employee_id", "employee_key",
                "start_date", "end_date", "status"
            ]
        ),
        "fact_headcount_monthly": (
            "fact_headcount_monthly.csv",
            [
                "date_key", "department_id",
                "headcount_start", "headcount_end"
            ]
        ),
    }

    # Load each dataset independently so one missing file does not
    # prevent checks on every other available dataset.
    for dataset, (filename, required_columns) in specifications.items():
        try:
            df = load_csv(filename)
            datasets[dataset] = df

            check_required_columns(
                df, dataset, required_columns
            )
        except Exception as exc:
            record_check(
                "dataset_load",
                dataset,
                "FAIL",
                f"{type(exc).__name__}: {exc}"
            )

    # Unique identifiers.
    unique_keys = {
        "dim_employee": "employee_key",
        "dim_department": "department_id",
        "dim_role": "role_id",
        "dim_date": "date_key",
        "fact_payroll": "payroll_item_id",
        "fact_attendance_monthly": "attendance_fact_id",
        "fact_leave": "leave_request_id",
    }

    for dataset, key in unique_keys.items():
        if dataset in datasets:
            check_unique_key(datasets[dataset], dataset, key)

    # Employee-key referential integrity, preserving SCD Type 2.
    employee = datasets.get("dim_employee")

    if employee is not None:
        for fact_name, record_columns in [
            (
                "fact_payroll",
                ["payroll_item_id", "employee_id", "period_end_date"]
            ),
            (
                "fact_attendance_monthly",
                ["attendance_fact_id", "employee_id", "period_end_date"]
            ),
            (
                "fact_leave",
                ["leave_request_id", "employee_id", "start_date", "end_date"]
            ),
        ]:
            if fact_name in datasets:
                check_foreign_key(
                    datasets[fact_name],
                    employee,
                    fact_name,
                    "dim_employee",
                    "employee_key",
                    record_columns
                )

        check_employee_history(employee)

    # Date-key integrity checks.
    date_dim = datasets.get("dim_date")

    if date_dim is not None:
        for fact_name in (
            "fact_payroll",
            "fact_headcount_monthly"
        ):
            if fact_name in datasets:
                check_foreign_key(
                    datasets[fact_name],
                    date_dim,
                    fact_name,
                    "dim_date",
                    "date_key"
                )

    # Department references in the monthly headcount fact.
    department = datasets.get("dim_department")
    headcount = datasets.get("fact_headcount_monthly")

    if department is not None and headcount is not None:
        check_foreign_key(
            headcount,
            department,
            "fact_headcount_monthly",
            "dim_department",
            "department_id"
        )

    # Save the full validation report.
    report = pd.DataFrame(results)
    output_path = LOG_DIR / "phase1_validation_report.csv"
    report.to_csv(output_path, index=False)

    print("\n" + "=" * 72)
    print("VALIDATION COMPLETE")
    print(f"Report saved to: {output_path}")

    if not report.empty:
        counts = report["status"].value_counts()
        for status in ("PASS", "REVIEW", "FAIL", "SKIP"):
            print(f"{status}: {int(counts.get(status, 0))}")

    print("Source CSV files were not modified.")
    print("=" * 72)


if __name__ == "__main__":
    main()
