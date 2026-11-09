# Step 6 - Quality Gate Review

Generated: 2026-10-22 11:25:24
Catalog: C:\Users\chede appliances\PulseIQ_Analytics\data\clean\03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - dq_checks_catalog.csv
Known issues: C:\Users\chede appliances\PulseIQ_Analytics\data\clean\03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx - dq_known_issues.csv
Catalog checks: 14
Known-issue rows: 11
PASS: 2; FAIL: 8; WARN: 4; MISSING: 0

| Check | Severity | Status | Bad rows | Known issue listed |
|---|---|---|---:|---|
| DQ-C01 Payroll equals ledger | Critical | FAIL | 5 | False |
| DQ-C02 Ledger balanced | Critical | PASS | 0 | False |
| DQ-C03 Unique payroll rows | Critical | FAIL | 2 | False |
| DQ-C04 No orphan employees | Critical | WARN | 4 | False |
| DQ-C05 No attendance after exit | Warning | FAIL | 4 | False |
| DQ-C06 Unpaid leave deducted | Warning | FAIL | 4 | False |
| DQ-C07 Invoice arithmetic | Warning | FAIL | 1 | False |
| DQ-C08 Expense arithmetic | Warning | FAIL | 1 | False |
| DQ-C09 Task dates sensible | Warning | FAIL | 20 | False |
| DQ-C10 Leave dates sensible | Warning | PASS | 0 | False |
| DQ-C11 AI feeds are fresh | Warning | WARN | 0 | False |
| DQ-C12 Dimension history does not overlap | Critical | FAIL | 1 | False |
| DQ-C13 Pipeline freshness | Critical | WARN | 0 | False |
| DQ-C14 Minimum group size | Critical | WARN | 0 | False |

## Sign-off
This report documents the review; unresolved FAIL/WARN results and known-issue reconciliation must be resolved before full sign-off.
