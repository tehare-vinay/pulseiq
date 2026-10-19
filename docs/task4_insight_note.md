# Task 4 — Attendance Trends Analysis

## Objective
Analyse attendance and leave patterns over time, identify department differences, review anomaly flags, and communicate findings for HR.

## Data coverage
- Attendance records: 7,343
- Attendance period: April 2025 to September 2026
- Departments: 11
- Overall weighted attendance rate: 94.0%

## Findings

### 1. Attendance varies over time
Monthly attendance rates ranged from approximately 92.64% to 95.35% in the available summary. The lowest observed month was May 2026 (92.64%); the highest was July 2025 (95.35%). HR should review staffing, leave coverage, and operational context around lower-attendance months before concluding that a seasonal pattern exists.

### 2. Department D08 has the lowest observed attendance
D08 recorded 90.60% attendance, the lowest among the 11 departments in the current summary. D07 followed at 92.34%. HR should review team-level workload, shift coverage, and approved leave records for these departments before attributing the difference to employee behaviour.

### 3. Attendance anomaly sample flags patterns that warrant review
The attendance-related sample contains 221 flagged records:
- PATTERN_SHIFT: 125
- NO_ATTENDANCE: 50
- LONG_UNPAID_ABSENCE: 43
- FREQUENT_LATE: 3

These are anomaly flags, not proof of misconduct or confirmed incidents. HR should validate individual records and relevant policies before taking action.

## Recommended HR actions
1. Review D08 and D07 attendance patterns with their managers.
2. Compare lower-attendance months with staffing levels, holidays, and leave approvals.
3. Validate anomaly flags against source records before contacting employees.
4. Monitor monthly attendance and late arrivals consistently.

## Limitations and uncertainty
- The attendance fact is monthly, not daily. It cannot establish weekday-level patterns.
- The anomaly sample is model-generated and should be treated as a review queue, not ground truth.
- Observed month-to-month variation does not by itself prove seasonality or explain its cause.
- Department comparisons may be affected by differences in team size and working schedules.
- Leave and attendance records should be reconciled before operational decisions.

## Deliverables created
- `logs/task4_monthly_summary.csv`
- `logs/task4_leave_by_type_status.csv`
- `logs/task4_attendance_anomalies.csv`
- `logs/task4_monthly_attendance_trend.csv`
- `logs/task4_department_attendance.csv`

## Remaining dashboard work
Build the Attendance & Leave dashboard in Superset using the verified warehouse/source data, add date and department filters where supported, show attendance trends and relevant anomaly flags, and export the dashboard definition into `dashboards/`.

## Status
Analysis outputs and initial insight note created. Final completion requires dashboard verification, export, and review of all deliverables.
