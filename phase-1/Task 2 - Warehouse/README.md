# PulseIQ Analytics — Task 2: Star-Schema Warehouse

## Objective
Build and validate a warehouse using dimension and fact tables, primary keys, foreign keys, employee-history handling, orphan checks, and row-count reconciliation.

## Main deliverables
- `schema.sql` — warehouse table definitions and keys.
- `star_schema.md` — star-schema diagram and declared join map.
- `task2_validation_queries.sql` — SQL validation queries.
- `task2_orphan_check_results.md` — orphan-check evidence.
- `task2_row_count_reconciliation.sql` — Task 1 to Task 2 row-count reconciliation.
- `task2_employee_history_validation_final.sql` — employee-history checks.
- `task2_history_and_orphans_notes.md` — history and unresolved-exception notes.

## Row-count reconciliation
The recorded reconciliation passed for all four fact tables:
- `fact_attendance_monthly`: 7,343 rows
- `fact_headcount_monthly`: 891 rows
- `fact_leave`: 3,439 passed rows from 3,441 input rows; 2 quarantined rows
- `fact_payroll`: 7,344 rows

## Outstanding source-data exceptions
- Two payroll records use `employee_key = -1` and remain unresolved.
- Four attendance records do not overlap the linked employee version's validity month and require source-owner review.
- The two invalid leave-date records remain quarantined until the source owner confirms the correct dates.

These exceptions must not be silently reassigned, deleted, or marked resolved without supporting evidence.

## Current status
Row-count reconciliation is recorded as PASS for all four fact tables. Employee-history and unknown-employee exceptions are documented but still require review. Do not describe these exceptions as fully resolved.
