# Task 3 — Data Quality Checks: Plain-English Review

Source: dq_checks_catalog.csv
Total catalog checks: 14

| ID | Check | What could go wrong? | Catalog severity |
|---|---|---|---|
| DQ-C01 | Payroll equals ledger | Monthly payroll cost differs from salary-related ledger expense. | Critical |
| DQ-C02 | Ledger balanced | Journal entry debits and credits differ. | Critical |
| DQ-C03 | Unique payroll rows | Duplicate employee/run payroll rows exist. | Critical |
| DQ-C04 | No orphan employees | Payroll employee cannot be found in employee dimension. | Critical |
| DQ-C05 | No attendance after exit | Attendance falls after the employee exit month. | Warning |
| DQ-C06 | Unpaid leave deducted | Unpaid absence is not reflected correctly in payroll LOP days. | Warning |
| DQ-C07 | Invoice arithmetic | Paid amount exceeds invoice total or balance is negative. | Warning |
| DQ-C08 | Expense arithmetic | Total does not equal amount excluding GST plus GST. | Warning |
| DQ-C09 | Task dates sensible | Completion precedes start, or a Done task has no completion date. | Warning |
| DQ-C10 | Leave dates sensible | Leave end date precedes leave start date. | Warning |
| DQ-C11 | AI feeds are fresh | Prediction as-of date or scoring timestamp violates freshness rule. | Warning |
| DQ-C12 | Dimension history does not overlap | Historical versions for one employee overlap. | Critical |
| DQ-C13 | Pipeline freshness | Latest successful load is older than the permitted 24 hours. | Critical |
| DQ-C14 | Minimum group size | An aggregate is shown for fewer than the permitted number of employees. | Critical |

## Implementation notes

1. DQ-C04 catalog SQL uses employee_id; Task 2 also requires employee_key-based historical joins. Implement referential integrity and employee identity consistency separately.
2. DQ-C05 must respect monthly fact grain and SCD Type 2 history. Do not remap employee versions without evidence.
3. DQ-C11 description mentions scored_at within 24 hours, but the catalog SQL example only checks as_of_date. Both rules need implementation.
4. DQ-C12 SQL example uses employee_key ordering to select version pairs. Validate actual date overlap independently of key ordering.
5. DQ-C13 description specifies the latest successful load, but the SQL example only shows MAX(finished_at). Filter to successful runs when implementing.
6. DQ-C14 is an aggregate privacy rule, not a normal row-level invalid-record check.

This is the catalog review. SQL implementation and tests will be performed in the following steps.
