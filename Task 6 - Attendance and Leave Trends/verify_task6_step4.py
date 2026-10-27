import pandas as pd
from pathlib import Path

root = Path("Task 6 - Attendance and Leave Trends")
clean = Path("data/clean/dim_date.csv")
att_file = root / "monthly_attendance_trends.csv"

if not clean.exists():
    raise FileNotFoundError(f"Missing source calendar: {clean}")
if not att_file.exists():
    raise FileNotFoundError(f"Missing attendance trends: {att_file}")

cal = pd.read_csv(clean, dtype=str).fillna("")
att = pd.read_csv(att_file, dtype=str).fillna("")

def col(df, options, label):
    for name in options:
        if name in df.columns:
            return name
    raise ValueError(f"Missing {label}. Available columns: {list(df.columns)}")

date_col = col(cal, ["date", "calendar_date"], "calendar date")
holiday_col = col(cal, ["is_holiday"], "holiday flag")
weekend_col = col(cal, ["is_weekend"], "weekend flag")
working_col = col(cal, ["is_working_day"], "working-day flag")

cal[date_col] = pd.to_datetime(cal[date_col], errors="coerce")
cal = cal[cal[date_col].notna()].copy()
cal["year_month"] = cal[date_col].dt.strftime("%Y-%m")

def yes(s):
    return s.astype(str).str.strip().str.upper().isin(["Y", "YES", "TRUE", "1"])

cal["holiday"] = yes(cal[holiday_col])
cal["weekend"] = yes(cal[weekend_col])
cal["working_day"] = yes(cal[working_col])

# Candidate means a holiday on Friday/Monday or immediately beside a weekend.
weekday = cal[date_col].dt.weekday
holiday_weekday = cal.loc[cal["holiday"], [date_col, "year_month"]].copy()
holiday_weekday["weekday"] = holiday_weekday[date_col].dt.weekday
weekend_dates = set(cal.loc[cal["weekend"], date_col].dt.normalize())
holiday_weekday["candidate"] = holiday_weekday.apply(
    lambda r: (
        r["weekday"] in (0, 4)
        or (r[date_col] - pd.Timedelta(days=1)).normalize() in weekend_dates
        or (r[date_col] + pd.Timedelta(days=1)).normalize() in weekend_dates
    ), axis=1
)

monthly = cal.groupby("year_month").agg(
    calendar_dates=(date_col, "size"),
    calendar_working_days=("working_day", "sum"),
    weekend_days=("weekend", "sum"),
    holidays=("holiday", "sum")
).reset_index()

candidate_counts = holiday_weekday.groupby("year_month")["candidate"].sum()
monthly["holiday_long_weekend_candidates"] = (
    monthly["year_month"].map(candidate_counts).fillna(0).astype(int)
)

att_month_col = next(
    (c for c in ["year_month", "month", "period_end_date"] if c in att.columns),
    None
)
if att_month_col is None:
    raise ValueError(f"Cannot identify month in attendance file: {list(att.columns)}")

if att_month_col == "period_end_date":
    att["year_month"] = pd.to_datetime(att[att_month_col], errors="coerce").dt.strftime("%Y-%m")
else:
    att["year_month"] = att[att_month_col].astype(str).str[:7]

rate_col = next(
    (c for c in ["attendance_pct", "attendance_rate_pct", "mean_attendance_pct",
                 "avg_attendance_pct", "attendance_rate"] if c in att.columns),
    None
)
if rate_col:
    att[rate_col] = pd.to_numeric(att[rate_col], errors="coerce")
    if att[rate_col].dropna().size and att[rate_col].dropna().max() <= 1:
        att[rate_col] = att[rate_col] * 100
    att_monthly = att.groupby("year_month", as_index=False)[rate_col].mean()
    att_monthly = att_monthly.rename(columns={rate_col: "attendance_rate_pct"})
else:
    att_monthly = att[["year_month"]].drop_duplicates()
    att_monthly["attendance_rate_pct"] = float("nan")

monthly = att_monthly.merge(monthly, on="year_month", how="left")
monthly["calendar_coverage"] = monthly["calendar_dates"].apply(
    lambda x: "PASS" if pd.notna(x) and x > 0 else "MISSING"
)

conflicts = int((cal["holiday"] & cal["working_day"]).sum())
missing_months = int((monthly["calendar_coverage"] == "MISSING").sum())
full_calendar = cal.copy()
full_calendar["holiday_long_weekend_candidate"] = False
candidate_dates = set(holiday_weekday.loc[holiday_weekday["candidate"], date_col])
full_calendar["holiday_long_weekend_candidate"] = (
    full_calendar["holiday"] & full_calendar[date_col].isin(candidate_dates)
)

full_calendar.to_csv(root / "task6_step4_full_calendar_validation.csv", index=False)
monthly.to_csv(root / "task6_holiday_long_weekend_summary.csv", index=False)

notes = [
    "# Task 6 — Step 4: Holiday and Long-Weekend Verification",
    "",
    "## Verification results",
    f"- Source calendar rows: {len(cal)}",
    f"- Source calendar date range: {cal[date_col].min().date()} to {cal[date_col].max().date()}",
    f"- Holiday dates: {int(cal['holiday'].sum())}",
    f"- Holiday dates that are also flagged working days: {conflicts}",
    f"- Attendance months checked: {len(monthly)}",
    f"- Attendance months without calendar coverage: {missing_months}",
    "",
    "## Interpretation",
    "- Long-weekend candidates are calendar indicators, not proof that a holiday caused an attendance change.",
    "- Attendance rate uses the governed metric denominator: employee scheduled working days.",
    "- Calendar working days are contextual calendar counts; they must not replace the sum of employee scheduled days.",
    "- Check holiday dates against attendance dips before drawing causal conclusions.",
    "",
    "## Evidence files",
    "- `task6_step4_full_calendar_validation.csv` — full date-level calendar",
    "- `task6_holiday_long_weekend_summary.csv` — attendance-month coverage and calendar summary",
    ""
]
(root / "task6_step4_holiday_notes.md").write_text("\n".join(notes), encoding="utf-8")

print("STEP 4 FINAL VERIFICATION")
print(f"Full calendar rows: {len(cal)}")
print(f"Holiday dates: {int(cal['holiday'].sum())}")
print(f"Holiday + working-day conflicts: {conflicts}")
print(f"Attendance months checked: {len(monthly)}")
print(f"Months with calendar coverage: {int((monthly['calendar_coverage'] == 'PASS').sum())}")
print(f"Months missing calendar coverage: {missing_months}")
print("\nMonthly coverage:")
print(monthly[["year_month", "calendar_dates", "holidays",
               "holiday_long_weekend_candidates", "calendar_coverage"]].to_string(index=False))
print("\nSaved:")
print(root / "task6_step4_full_calendar_validation.csv")
print(root / "task6_holiday_long_weekend_summary.csv")
print(root / "task6_step4_holiday_notes.md")
