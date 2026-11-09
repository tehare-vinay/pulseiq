# PulseIQ Analytics â€” Task 2 Final Status

Generated: 2026-10-23 17:20:48

## Deliverables
- PostgreSQL warehouse schema and loader
- Star-schema diagram and join-map documentation
- Business questions and validation SQL
- Row-count reconciliation and employee-history validation evidence
- Orphan-check and exception documentation

## Latest recorded reconciliation
| Fact table | Expected accepted rows | Warehouse rows | Result |
|---|---:|---:|---|
| fact_attendance_monthly | 7343 | 7343 | PASS |
| fact_headcount_monthly | 891 | 891 | PASS |
| fact_leave | 3439 | 3439 | PASS; 2 invalid source rows quarantined |
| fact_payroll | 7344 | 7344 | PASS |

## Exceptions â€” do not silently alter source data
1. Four attendance history records (FA-X0001 to FA-X0004) have fact months outside the linked employee dimension validity period. Pending source-owner review.
2. Two payroll records (PI-X0003, PI-X0004) refer to EMP-9001 and EMP-9002, absent from the supplied employee dimension; employee_key remains -1. Pending source-owner review.
3. Two invalid leave rows are quarantined with reason leave_end_before_start.

## Sign-off
Warehouse row-count reconciliation is recorded as PASS for all four fact tables. Task 2 is **substantially complete with documented source exceptions**, not exception-free. Do not change or delete source rows or invent employee keys without written source-owner confirmation.

Before submission, run the current validation SQL against the local database and confirm the official updated task instructions and submission form requirements.
