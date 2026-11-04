import os
from pathlib import Path
import pandas as pd
import psycopg2

ROOT = Path.cwd()
TASK = ROOT / "Task 13 - Cross Department Impact View"

sql_file = TASK / "task13_metrics.sql"
ref_file = ROOT / "data" / "clean" / "reference_summary_dept_month.csv"

if not sql_file.exists():
    raise FileNotFoundError(f"Step 3 SQL not found: {sql_file}")

if not ref_file.exists():
    raise FileNotFoundError(f"Reference CSV not found: {ref_file}")

sql = sql_file.read_text(encoding="utf-8")
if not sql.strip():
    raise ValueError("Step 3 SQL file is empty.")

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="pulseiq_warehouse",
    user="pulseiq_user",
    password=os.getenv("PGPASSWORD", "")
)

try:
    actual = pd.read_sql_query(sql, conn)
finally:
    conn.close()

reference = pd.read_csv(ref_file)

actual["month_start"] = pd.to_datetime(actual["month_start"]).dt.to_period("M").dt.to_timestamp()
reference["month"] = pd.to_datetime(reference["month"]).dt.to_period("M").dt.to_timestamp()

actual = actual.rename(columns={
    "month_start": "month",
    "overtime_cost": "overtime_pay"
})

keys = ["department_id", "month"]

for name, df in [("Actual", actual), ("Reference", reference)]:
    duplicates = df.duplicated(keys, keep=False)
    if duplicates.any():
        print(f"\n{name} duplicate department-month keys:")
        print(df.loc[duplicates, keys].to_string(index=False))

metrics = [
    "employer_cost",
    "gross_pay",
    "overtime_pay",
    "overtime_hours",
    "headcount_end",
    "attrition_rate_monthly_pct"
]

available = [m for m in metrics if m in actual.columns and m in reference.columns]
missing_actual = [m for m in metrics if m not in actual.columns]
missing_reference = [m for m in metrics if m not in reference.columns]

comparison = actual[keys + available].merge(
    reference[keys + available],
    on=keys,
    how="outer",
    suffixes=("_actual", "_reference"),
    indicator=True
)

comparison["row_status"] = comparison["_merge"].map({
    "both": "MATCHED_KEY",
    "left_only": "ACTUAL_ONLY",
    "right_only": "REFERENCE_ONLY"
})

for metric in available:
    a = pd.to_numeric(comparison[f"{metric}_actual"], errors="coerce")
    r = pd.to_numeric(comparison[f"{metric}_reference"], errors="coerce")
    comparison[f"{metric}_difference"] = a - r
    comparison[f"{metric}_match"] = (
        a.notna() & r.notna() & ((a - r).abs() <= 0.01)
    )

summary_rows = []
for metric in available:
    valid = comparison[
        comparison["row_status"] == "MATCHED_KEY"
    ]
    summary_rows.append({
        "metric": metric,
        "compared_rows": int(valid[f"{metric}_difference"].notna().sum()),
        "matching_rows": int(valid[f"{metric}_match"].sum()),
        "different_rows": int(
            (valid[f"{metric}_difference"].notna() &
             ~valid[f"{metric}_match"]).sum()
        ),
        "null_actual": int(valid[f"{metric}_actual"].isna().sum()),
        "null_reference": int(valid[f"{metric}_reference"].isna().sum())
    })

summary = pd.DataFrame(summary_rows)

TASK.mkdir(exist_ok=True)
detail_path = TASK / "task13_step4_comparison_detail.csv"
summary_path = TASK / "task13_step4_comparison_summary.csv"
notes_path = TASK / "task13_step4_difference_notes.txt"

comparison.to_csv(detail_path, index=False)
summary.to_csv(summary_path, index=False)

notes = [
    "TASK 13 - STEP 4 REFERENCE COMPARISON",
    f"Actual rows: {len(actual)}",
    f"Reference rows: {len(reference)}",
    f"Actual unique department-month keys: {actual[keys].drop_duplicates().shape[0]}",
    f"Reference unique department-month keys: {reference[keys].drop_duplicates().shape[0]}",
    f"Matched keys: {(comparison['_merge'] == 'both').sum()}",
    f"Actual-only keys: {(comparison['_merge'] == 'left_only').sum()}",
    f"Reference-only keys: {(comparison['_merge'] == 'right_only').sum()}",
    "",
    "Metrics compared: " + ", ".join(available),
    "Metrics missing from actual output: " + ", ".join(missing_actual),
    "Metrics missing from reference: " + ", ".join(missing_reference),
    "",
    "Metric comparison summary:",
    summary.to_string(index=False),
    "",
    "Tolerance used: 0.01 for numeric metric comparisons.",
    "This tolerance is a comparison setting, not a confirmed unlock_PQ-13 rule.",
    "unlock_PQ-13 was not found; its validation instructions remain unverified."
]

notes_path.write_text("\n".join(notes), encoding="utf-8")

print("\nREFERENCE COMPARISON FINISHED")
print("\nROW AND KEY SUMMARY:")
print(f"Actual rows: {len(actual)}")
print(f"Reference rows: {len(reference)}")
print(f"Matched keys: {(comparison['_merge'] == 'both').sum()}")
print(f"Actual-only keys: {(comparison['_merge'] == 'left_only').sum()}")
print(f"Reference-only keys: {(comparison['_merge'] == 'right_only').sum()}")

print("\nMETRIC COMPARISON:")
print(summary.to_string(index=False))

print("\nFILES CREATED:")
print(detail_path)
print(summary_path)
print(notes_path)


