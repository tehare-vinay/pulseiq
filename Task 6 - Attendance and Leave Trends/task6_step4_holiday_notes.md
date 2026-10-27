# Task 6 — Step 4: Holiday and Long-Weekend Verification

## Verification results
- Source calendar rows: 2557
- Source calendar date range: 2020-01-01 to 2026-12-31
- Holiday dates: 19
- Holiday dates that are also flagged working days: 0
- Attendance months checked: 18
- Attendance months without calendar coverage: 0

## Interpretation
- Long-weekend candidates are calendar indicators, not proof that a holiday caused an attendance change.
- Attendance rate uses the governed metric denominator: employee scheduled working days.
- Calendar working days are contextual calendar counts; they must not replace the sum of employee scheduled days.
- Check holiday dates against attendance dips before drawing causal conclusions.

## Evidence files
- `task6_step4_full_calendar_validation.csv` — full date-level calendar
- `task6_holiday_long_weekend_summary.csv` — attendance-month coverage and calendar summary
