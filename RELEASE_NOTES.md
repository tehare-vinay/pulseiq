# PulseIQ Analytics – Release Notes v1.0.0

## 1. What Is Included

- PostgreSQL analytics warehouse and data model.
- Data quality checks and validation framework.
- Streamlit dashboards for people, attendance, attrition, productivity, payroll, expenses, profit and loss, receivables and cash flow.
- Cross-department impact analysis.
- AI-generated anomaly and forecast insights for human review.
- Executive scorecard and board presentation.
- Project documentation and phase-wise reports.

## 2. What Is Not Included

- Automatic correction of all data-quality failures.
- Unapproved permanent exclusions of payroll records.
- Resolution of all outstanding reconciliation differences.
- Guaranteed predictive decisions.
- Production deployment or integrations not verified in this release.

## 3. Known Limits

- Live data-quality checks returned 2 PASS, 8 FAIL and 4 WARN.
- June 2026 payroll-to-ledger reconciliation has an unresolved difference of ₹18,450.
- Payroll reconciliation returned 18 conditional PASS results using four unapproved candidate exclusions.
- Task 13 independent metric reconciliation remains pending.
- ETL freshness and manager aggregate privacy checks require further verification.
- AI-generated anomaly and forecast outputs require human review.

## 4. Release Validation

- Live data-quality checks executed.
- Task 11 P&L validation queries and account audit executed.
- June 2026 source-level reconciliation investigated.
- Task 9 payroll reconciliation executed as a controlled exclusion test.
- Task 13 cross-department validation executed.

Unresolved failures, warnings and differences are documented rather than represented as resolved.

## 5. Release Information

- Release: v1.0.0
- Project: PulseIQ Analytics
- Release scope: Phase 1 through Phase 4, Task 20
