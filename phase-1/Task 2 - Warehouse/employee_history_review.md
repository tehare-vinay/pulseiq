# Task 2 — Final Employee History Review

## Employee history join rule
Fact tables join to dim_employee using employee_key, not employee_id.
For monthly facts, validate whether the reporting month overlaps the linked employee version.

## Final validation
- Payroll non-unknown rows checked: 7,342
- Payroll month-overlap issues: 0 — PASS
- Attendance rows checked: 7,343
- Attendance month-overlap exceptions: 4 — documented below
- Missing dimension keys: 0
- Employee ID mismatches: 0
- Department mismatches: 0

## Documented attendance exceptions

| Attendance fact ID | Employee ID | Employee key | Fact month end | Linked version end | Disposition |
|---|---|---:|---|---|---|
| FA-X0001 | EMP-0476 | 101234 | 2026-03-31 | 2026-02-27 | Source confirmation required |
| FA-X0002 | EMP-0183 | 100617 | 2026-03-31 | 2026-02-17 | Source confirmation required |
| FA-X0003 | EMP-0540 | 101330 | 2025-11-30 | 2025-10-28 | Source confirmation required |
| FA-X0004 | EMP-0490 | 101251 | 2025-12-31 | 2025-11-17 | Source confirmation required |

These four rows have no overlap between the reporting month and the linked employee version. They are documented source-review exceptions, not orphan keys. Their employee keys have not been changed. Do not remap or delete them without source-owner confirmation.

## Reconciliation
The four warehouse fact tables reconcile to Task 1 passed rows:
- fact_payroll: 7,344
- fact_attendance_monthly: 7,343
- fact_headcount_monthly: 891
- fact_leave: 3,439

All four row-count differences are zero. Orphan checks previously returned zero orphan and null keys for all seven checked relationships.

## Final status
Employee-key join validation: PASS for checked key and department consistency.
Payroll month-overlap validation: PASS.
Attendance history: four explicitly documented source-review exceptions remain.
Row-count reconciliation: PASS.
Orphan checks: PASS.
