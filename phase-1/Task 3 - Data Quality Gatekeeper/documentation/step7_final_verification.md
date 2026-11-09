# Task 3 - Step 7 Final Verification

Generated: 2026-10-22 11:27:49
Source catalog: C:\Users\chede appliances\PulseIQ_Analytics\data\clean\03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - dq_checks_catalog.csv
Checks in catalog: 14
Latest results matched: 14
PASS: 2; FAIL: 8; WARN: 4; MISSING: 0
Critical checks currently FAIL: 3

## Severity and verification matrix
| Check | Severity | Status | Bad rows |
|---|---|---|---:|
| DQ-C01 Payroll equals ledger | Critical | FAIL | 5 |
| DQ-C02 Ledger balanced | Critical | PASS | 0 |
| DQ-C03 Unique payroll rows | Critical | FAIL | 2 |
| DQ-C04 No orphan employees | Critical | WARN | 4 |
| DQ-C05 No attendance after exit | Warning | FAIL | 4 |
| DQ-C06 Unpaid leave deducted | Warning | FAIL | 4 |
| DQ-C07 Invoice arithmetic | Warning | FAIL | 1 |
| DQ-C08 Expense arithmetic | Warning | FAIL | 1 |
| DQ-C09 Task dates sensible | Warning | FAIL | 20 |
| DQ-C10 Leave dates sensible | Warning | PASS | 0 |
| DQ-C11 AI feeds are fresh | Warning | WARN | 0 |
| DQ-C12 Dimension history does not overlap | Critical | FAIL | 1 |
| DQ-C13 Pipeline freshness | Critical | WARN | 0 |
| DQ-C14 Minimum group size | Critical | WARN | 0 |

## Final decision
NOT READY FOR SIGN-OFF: missing results or critical failures remain.

## Scope and limitations
This step classifies checks and records the latest runtime verification. It does not repair source data, suppress failures, or prove all planted known issues were detected. Review the check details and Step 6 known-issue comparison before declaring Task 3 complete.
