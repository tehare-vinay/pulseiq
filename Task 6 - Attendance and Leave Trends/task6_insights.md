# Task 6 — Attendance and Leave Trends

## Scope and evidence

Analysis period: 2025-04 to 2026-09.

- Monthly attendance records: 18 months.
- Monthly leave summary records: 212 month/type/status combinations.
- Holiday calendar records: 19 holiday dates.

Source files:
- monthly_attendance_trends.csv
- monthly_leave_trends.csv
- holiday_calendar_evidence.csv

## Finding 1 — Lowest attendance

- Month: 2026-05
- Calculated attendance: 92.64%
- Late arrivals: 476
- Overtime: 492.5 hours.

This month is a candidate for further investigation. The monthly aggregate alone does not establish the cause.

## Finding 2 — Largest month-on-month attendance decline

- Month: 2025-10
- Attendance: 93.76%
- Change from previous month: -1.5 percentage points.
- Late arrivals: 537.

This is the largest observed monthly decline in the available series. Validate department-level contributions before attributing a cause.

## Finding 3 — Highest overtime

- Month: 2025-12
- Overtime: 787.0 hours.
- Attendance: 93.58%.

A high total may reflect workforce size or workload. Compare departments and normalize where appropriate before calling it an operational anomaly.

## Leave trend

- Month with the most approved leave days: 2026-01
- Approved leave days: 573

Leave days are summarized by the leave request start month. Requests spanning multiple months are not allocated across individual dates in this summary.

## Holiday and long-weekend limitations

The holiday calendar contains 19 holiday dates. Adjacent calendar flags are included in the evidence file. These flags should be checked before labeling a date sequence as a long weekend.

Monthly attendance data cannot establish daily attendance changes on or around holidays. Therefore, this analysis does not claim that holidays caused attendance changes.

## Validation notes

- Attendance percentage is calculated as total present days divided by total scheduled days, multiplied by 100.
- This weighted result may differ from the average source attendance rate.
- Monthly aggregates can hide department-level differences and small-group effects.
- The three findings above are investigation candidates, not proof of root cause.

## Evidence files

- monthly_attendance_trends.csv
- monthly_leave_trends.csv
- holiday_calendar_evidence.csv
- task6_insights.md

## Task 6 - Step 5: Three unusual months

### 1. October 2025 - Attendance decline
Attendance decreased from 95.26% in September 2025 to 93.76% in October 2025, a decline of 1.50 percentage points. The calendar summary records 3 holidays and 1 holiday/long-weekend candidate for October. These dates may provide context, but the available aggregate data does not prove that holidays caused the decline. Recommended follow-up: compare department-level attendance changes and check whether the decline is concentrated in particular departments.

### 2. December 2025 - Overtime spike
Recorded overtime reached 787.0 hours in December 2025, compared with 560.0 hours in November: an increase of 227.0 hours, or approximately 40.5%. December had 1 holiday and 0 holiday/long-weekend candidates in the calendar summary. Possible explanations to investigate include workload peaks, staffing coverage, or project deadlines. The current data does not establish which explanation is correct. Recommended follow-up: compare overtime by department and review payroll/workload context.

### 3. January 2026 - Approved leave spike
Approved leave reached 573 days in January 2026, compared with 421 days in December 2025: an increase of 152 days, or approximately 36.1%. January had 3 holidays and 1 holiday/long-weekend candidate. Holiday timing may be relevant context, but it is not proof of the cause. Recommended follow-up: compare leave types and department-level leave patterns before drawing a conclusion.

### Interpretation and limitations
These are three unusual patterns identified from monthly aggregate data. The explanations above are hypotheses to investigate, not confirmed causes. Calendar context is used to interpret attendance trends, not to claim that holidays caused attendance changes. Department-level comparisons should be checked before making operational recommendations.
