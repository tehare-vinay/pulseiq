# Task 2 â€” Orphan Key Check Results

## Summary

The warehouse orphan-key checks were executed against the fact and dimension tables.

- 11 checks returned zero orphan rows.
- 1 check returned 2 orphan rows: `fact_payroll` to `dim_employee`.

## Confirmed Orphan Rows

| Payroll Item ID | Employee ID | Employee Key | Period End Date | Department ID |
|---|---|---|---|---|
| PI-X0003 | EMP-9001 | -1 | 2026-04-30 | D01 |
| PI-X0004 | EMP-9002 | -1 | 2025-12-31 | D09 |

## Explanation

Both payroll records contain `employee_key = -1`, but no matching row exists in `dim_employee` for that key. The employee IDs `EMP-9001` and `EMP-9002` were also not found in the employee dimension during the checks performed.

These records remain unresolved. They must not be assigned to another employee without supporting source evidence. The source records and the intended unknown-member handling should be reviewed before any warehouse correction.

## Validation Status

- 11 orphan checks returned zero rows.
- 2 payroll employee-key orphans remain unresolved.
- Employee-history validity is a separate check and must be documented separately.
- Final fact-row-count reconciliation against Task 1: PASS for all four fact tables; differences are zero. See task2_row_count_reconciliation.sql.


## Unresolved payroll employee references — source review required

The warehouse contains two payroll records with employee_key = -1 because the employee IDs were not found in the supplied raw or clean dim_employee source files.

| payroll_item_id | employee_id | employee_key | period_end_date | status |
|---|---|---:|---|---|
| PI-X0003 | EMP-9001 | -1 | 2026-04-30 | Pending source-owner review |
| PI-X0004 | EMP-9002 | -1 | 2025-12-31 | Pending source-owner review |

Action: Preserve both source records and the unknown-key mapping. Do not assign another employee_key or delete these records without source-owner confirmation. These are documented data exceptions, not silently resolved matches.

