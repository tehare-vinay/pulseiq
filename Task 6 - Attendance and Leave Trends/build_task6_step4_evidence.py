import pandas as pd
from pathlib import Path

root = Path("Task 6 - Attendance and Leave Trends")
evidence = root / "evidence"
calendar_file = root / "holiday_calendar_evidence.csv"
attendance_file = root / "monthly_attendance_trends.csv"

if not calendar_file.exists():
    raise FileNotFoundError(f"Missing file: {calendar_file}")
if not attendance_file.exists():
    raise FileNotFoundError(f"Missing file: {attendance_file}")

cal = pd.read_csv(calendar_file, dtype=str).fillna("")
att = pd.read_csv(attendance_file, dtype=str).fillna("")

def find_col(df, candidates, label):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"Cannot find {label}. Available columns: {list(df.columns)}")

date_col = find_col(cal, ["calendar_date", "date"], "calendar date")
month_col = find_col(cal, ["year_month", "month"], "calendar month")
holiday_col = find_col(cal, ["is_holiday"], "holiday flag")
weekend_col = find_col(cal, ["is_weekend"], "weekend flag")
working_col = find_col(cal, ["is_working_day"], "working-day flag")

cal[date_col] = pd.to_datetime(cal[date_col], errors="coerce")
cal = cal[cal[date_col].notna()].copy()
cal[month_col] = cal[date_col].dt.strftime("%Y-%m")

def is_y(series):
    return series.astype(str).str.strip().str.upper().isin(["Y", "YES", "TRUE", "1"])

cal["_holiday"] = is_y(cal[holiday_col])
cal["_weekend"] = is_y(cal[weekend_col])
cal["_working"] = is_y(cal[working_col])

# Adjacent weekend indicator: flag holidays directly next to a weekend.
prev_col = next((c for c in ["previous_day_weekend"] if c in cal.columns), None)
next_col = next((c for c in ["next_day_weekend"] if c in cal.columns), None)
if prev_col:
    cal["_prev_weekend"] = is_y(cal[prev_col])
else:
    cal["_prev_weekend"] = cal[date_col].sub(pd.Timedelta(days=1)).dt.weekday.isin([5, 6])
if next_col:
    cal["_next_weekend"] = is_y(cal[next_col])
else:
    cal["_next_weekend"] = cal[date_col].add(pd.Timedelta(days=1)).dt.weekday.isin([5, 6])

cal["_holiday_near_weekend"] = cal["_holiday"] & (
    cal["_prev_weekend"] | cal["_next_weekend"] |
    cal[date_col].dt.weekday.isin([4, 0])
)

holiday_rows = cal[cal["_holiday"]].copy()
summary = cal.groupby(month_col).agg(
    calendar_days=(date_col, "size"),
    calendar_working_days=("_working", "sum"),
    weekend_days=("_weekend", "sum"),
    holidays=("_holiday", "sum"),
    holidays_adjacent_to_weekend=("_holiday_near_weekend", "sum")
).reset_index().rename(columns={month_col: "year_month"})

# Match monthly attendance trends with calendar counts.
att_month_col = find_col(att, ["year_month", "leave_month", "month"], "attendance month")
rate_col = next((c for c in [
    "attendance_pct", "attendance_rate_pct", "attendance_rate",
    "mean_attendance_pct", "avg_attendance_pct"
] if c in att.columns), None)

if rate_col:
    att["year_month"] = att[att_month_col].astype(str).str[:7]
    att[rate_col] = pd.to_numeric(att[rate_col], errors="coerce")
    # If the source stores a 0–1 ratio, convert to percentage.
    if att[rate_col].dropna().size and att[rate_col].dropna().max() <= 1:
        att[rate_col] = att[rate_col] * 100
    att_monthly = att.groupby("year_month", as_index=False)[rate_col].mean()
    att_monthly = att_monthly.rename(columns={rate_col: "attendance_rate_pct"})
    summary = summary.merge(att_monthly, on="year_month", how="left")

summary.to_csv(root / "task6_holiday_long_weekend_summary.csv", index=False)
holiday_rows.to_csv(root / "holiday_calendar_evidence.csv", index=False)

total_holidays = int(cal["_holiday"].sum())
adjacent_holidays = int(cal["_holiday_near_weekend"].sum())
bad_flags = int((cal["_holiday"] & cal["_working"]).sum())

lines = [
    "# Task 6 — Step 4: Holiday and Long-Weekend Evidence",
    "",
    "## Method",
    "- Holiday dates come from the governed `dim_date` calendar evidence.",
    "- Long-weekend candidates are holidays adjacent to a weekend, plus Friday/Monday holidays.",
    "- Calendar flags are used to interpret attendance trends; they do not prove that a holiday caused a dip.",
    "- Attendance rate uses the governed attendance metric and its scheduled-working-day denominator.",
    "",
    "## Validation",
    f"- Calendar date rows inspected: {len(cal)}",
    f"- Holiday dates flagged: {total_holidays}",
    f"- Holiday/long-weekend candidate dates: {adjacent_holidays}",
    f"- Dates flagged both holiday and working day: {bad_flags}",
    "",
    "## Monthly evidence",
    "| Month | Holidays | Weekend days | Calendar working days | Holiday/long-weekend candidates | Attendance rate (%) |",
    "|---|---:|---:|---:|---:|---:|"
]
for _, r in summary.iterrows():
    rate = r.get("attendance_rate_pct", float("nan"))
    rate_text = f"{rate:.2f}" if pd.notna(rate) else "Not available"
    lines.append(
        f"| {r['year_month']} | {int(r['holidays'])} | {int(r['weekend_days'])} | "
        f"{int(r['calendar_working_days'])} | {int(r['holidays_adjacent_to_weekend'])} | {rate_text} |"
    )

lines += [
    "",
    "## Interpretation and limitation",
    "Check months with lower attendance against this calendar before describing the dip as an operational issue. "
    "A holiday overlap is contextual evidence, not proof of causation. If holiday and working-day flags conflict, "
    "review the source calendar definition before changing source records.",
    "",
    "## Files",
    "- `holiday_calendar_evidence.csv` — date-level holiday/calendar flags",
    "- `task6_holiday_long_weekend_summary.csv` — monthly calendar and attendance comparison",
    "- `task6_step4_holiday_notes.md` — this method and interpretation note",
    ""
]
(root / "task6_step4_holiday_notes.md").write_text("\n".join(lines), encoding="utf-8")

print("STEP 4 VALIDATION")
print(f"Calendar rows: {len(cal)}")
print(f"Holiday dates: {total_holidays}")
print(f"Holiday/long-weekend candidates: {adjacent_holidays}")
print(f"Holiday AND working-day flag conflicts: {bad_flags}")
print(f"Monthly summary rows: {len(summary)}")
print("\nSaved:")
print(root / "task6_holiday_long_weekend_summary.csv")
print(root / "task6_step4_holiday_notes.md")
