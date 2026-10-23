# Task 2 — Employee history and row-count reconciliation notes

## Employee history

Payroll and attendance are monthly-grain facts. Their `period_end_date` is the last calendar day of the month; it is not a daily transaction date. A fact can therefore end after an employee's `valid_to` when the employee left during that month. For this dataset, validate that the `employee_key` version overlaps the fact month, and independently compare the fact's source `employee_id` and source `department_id` against that exact dimension version.

The supplied clean source confirms zero employee-ID mismatches and zero department mismatches for linked payroll and attendance keys (excluding the two documented payroll `employee_key = -1` placeholders). All 82 payroll date-end mismatches overlap the fact month. Of the 85 attendance date-end mismatches, 81 overlap the fact month; four records do not overlap any validity month and must remain flagged for source review:

| Attendance record | Employee | Fact month end | Linked version valid_to | Decision |
|---|---|---|---|---|
| FA-X0001 | EMP-0476 | 2026-03-31 | 2026-02-27 | Preserve and flag; no valid version for March 2026 |
| FA-X0002 | EMP-0183 | 2026-03-31 | 2026-02-17 | Preserve and flag; no valid version for March 2026 |
| FA-X0003 | EMP-0540 | 2025-11-30 | 2025-10-28 | Preserve and flag; no valid version for November 2025 |
| FA-X0004 | EMP-0490 | 2025-12-31 | 2025-11-17 | Preserve and flag; no valid version for December 2025 |

Do not assign a different `employee_key` to these four rows without confirmation from the data owner. Their source department agrees with the linked dimension version; the unresolved problem is that the monthly attendance record occurs after that employee version ended. This is a documented source exception, not an orphan foreign key.

## Row counts

Task 1 must quarantine the two `fact_leave` records with `end_date < start_date` and record the reason `leave_end_before_start`. The raw input remains unchanged. The resulting Task 1 clean/passed count is 3,439 leave rows from 3,441 input rows; the other three declared facts pass through at their full counts. After rerunning the patched Task 1 ETL, `logs/etl_row_count_summary.csv` should show the two rejected leave rows, and the reconciliation SQL should report PASS for all four fact tables.
