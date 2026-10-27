# Task 6 — Attendance and Leave Trends

## Files
- `monthly_attendance_trends.csv`: monthly attendance, late arrivals and overtime.
- `monthly_leave_trends.csv`: leave requests and days by month, leave type and status.
- `holiday_calendar_evidence.csv`: holiday dates and adjacent calendar flags.
- `task6_insights.md`: calculated findings, interpretation and limitations.

## Reproduce
Run the SQL extraction queries against the existing PostgreSQL warehouse and export the three CSV files again before regenerating the insights report.

## Important
These are aggregate analyses. Do not infer individual employee behavior or claim that holidays caused attendance changes from monthly data alone. Review source data and department-level results before making business decisions.


---

# Task 6 — Step 1: Governed Metric Views and Denominator Rule

## Status
The existing attendance metric view was updated and its basic validation passed.

## Source data dictionary
- `dim_date.is_working_day`: Y if Monday–Friday and not a holiday.
- `fact_attendance_monthly.scheduled_days`: Working days the employee was scheduled in the month.
- `fact_attendance_monthly.present_days`: Days present (office or work from home).
- `fact_attendance_monthly.attendance_rate`: (Present days + 0.5 x half days) / scheduled days.

## Attendance denominator
The metric uses the employee-level `scheduled_days` denominator:
`100 x SUM(present days + 0.5 x half-day count) / SUM(scheduled_days)`

Calendar working days are used as calendar context, not as a replacement for employee-level scheduled days.

## Governed metric update
View: `public.metric_m13_attendance_rate`
SQL evidence: `task6_attendance_denominator_rule.sql`

Validation result after view creation:
- Metric rows: 180
- Periods: 18
- Minimum attendance rate: 80.87%
- Maximum attendance rate: 98.48%

## Business-rule caveat
The source dictionary describes the attendance formula using half-days, while the available source column is named `half_days_unpaid`. Confirm with the source owner that this field represents the half-day count intended by the formula before treating the formula as fully business-approved.

## Completion status
- Existing governed attendance metric inspected and updated.
- Required overtime and leave-by-type metric views were added earlier.
- Basic attendance view validation passed.
- Half-day field meaning requires source-owner confirmation.
