# Task 13 - Step 3 Validation

## Objective
Add overtime cost and leave days per head to the department-month dataset.

## Metrics Added
- Overtime cost: SUM(overtime_pay) by department and month.
- Leave days: Approved leave days allocated by working date.
- Average headcount: (headcount_start + headcount_end) / 2.
- Leave days per head: leave_days / average_headcount.

## Validation Results
| Check | Result |
|---|---:|
| Headcount department-month rows | 198 |
| Unique grains | 198 |
| Missing headcount | 0 |
| Duplicate source grains | 0 |

## Source Coverage
- Headcount contains historical data from January 2020.
- Payroll and attendance common reporting period starts April 2025.
- Combined dataset contains 203 department-month rows after the reporting-period filter.

## Limitations
- Source coverage differs across datasets.
- NULL metrics are not automatically converted to zero.
- Leave days per head denominator uses average headcount.
- Independent metric reconciliation remains pending.
