# Task 9 – Payroll Cost Dashboard and Reconciliation

## 1. Objective

Build a payroll cost dashboard in the existing Task 5 Streamlit application. Display gross pay, net pay, employer cost, department-wise and monthly summaries, and cost per employee. Compare monthly payroll totals with the reconciliation answer key, investigate data-quality issues, and document all exclusions and remaining differences.

## 2. Dashboard Implementation

**Dashboard page:** `Task 5 - First Dashboard/pages/5_Payroll_Cost.py`

The payroll page is part of the existing Task 5 dashboard; no separate dashboard application is required.

The page includes:
- Gross Pay, Net Pay and Employer Cost summaries.
- Department-wise payroll cost.
- Monthly payroll cost trend.
- Cost per employee and its monthly trend.
- Aggregate totals and averages rather than individual employee salary details.

**Implementation status:** The dashboard and charts are visible in the screenshots reviewed. Code-level calculation and privacy validation should be confirmed before claiming full validation.

## 3. Governed Metrics and Minimum Group Size

The existing governed metric views include:
- `metric_m09_payroll_cost`
- `metric_m10_cost_per_head`

The employer-cost metric view groups payroll by month and department and suppresses groups with fewer than five distinct employees. The cost-per-head metric applies the same minimum-group-size condition.

The current employer-cost view provides employer cost only; gross pay and net pay must also be sourced from appropriate governed metric views for the dashboard.

**Status:** The SQL definitions of all four governed payroll metric views were inspected. Gross pay, net pay, employer cost and cost per head are sourced from their respective governed views. Each view applies a minimum group-size condition of five distinct employees. The dashboard queries these four views. Final validation of cost-per-head aggregation is still required.

## 4. Reconciliation Method

**Answer key:** `data/clean/reconciliation_answer_key.csv`

The monthly payroll actuals were compared with the answer key for 18 months. Differences are calculated as:

`Actual payroll total − Answer-key total`

The comparison covers:
- Employees paid.
- Gross pay.
- Net pay.
- Employer cost.

## 5. Reconciliation Results

Four months have recorded differences:

| Month | Employee difference | Gross pay difference | Net pay difference | Employer cost difference |
|---|---:|---:|---:|---:|
| 2025-05 | 0 | 60,013.15 | 58,013.15 | 61,813.15 |
| 2025-12 | 1 | 96,527.42 | 94,527.42 | 98,327.42 |
| 2026-02 | 0 | 153,011.89 | 137,513.27 | 154,811.89 |
| 2026-04 | 0 | 96,015.00 | 95,815.00 | 96,015.00 |

These values reflect the recorded reconciliation output and should be rechecked against the latest script output before final submission. The April 2026 employee-count result also requires verification.

**Reconciliation status:** Four monthly differences remain unresolved. The payroll totals must not be described as fully reconciled.

## 6. Row Investigation and Data Quality
Candidate payroll records were investigated using employee-month counts, same-run counts, payroll item IDs, run IDs, and employee dimension mapping. The four investigated candidate records each had one employee-month row and one same-run row. Multiple payroll records alone should not be treated as proof of invalid payment without supporting evidence.

- No payroll rows have been deleted from the source table.
- No row has been confirmed invalid solely because its amount matches a reconciliation difference.
- Candidate records and observed differences should be recorded in the existing evidence files.
- Any future exclusion must identify the payroll item, affected month, reason, and supporting evidence.

## 7. Official Validation Material

The task instructions refer to `unlock_PQ-09` in `04_Validation_Vault`. The file was not found in the project folders searched.

The available reconciliation answer key has been used for monthly comparisons, but it has not been confirmed as a substitute for the official unlock material.

**Status:** Official unlock validation remains unavailable. No unsupported exclusion decision has been made.

## 8. Finance Communication

The payroll reconciliation identified differences between actual payroll totals and the reconciliation answer key for four months. Candidate records are being reviewed against authoritative validation evidence before any exclusion is made. Remaining differences will be reported transparently, and the source payroll data will remain unchanged unless an exclusion is justified.

## 9. Completion Checklist

| Requirement | Status |
|---|---|
| Payroll page in existing Task 5 dashboard | Implemented; screenshots reviewed |
| Gross, net and employer-cost summaries | Visible in dashboard; governed metric usage requires code verification |
| Department and monthly analysis | Visible in dashboard |
| Cost per employee and monthly trend | Visible in dashboard |
| Individual salary privacy | No individual salary details visible in reviewed screenshots |
| Minimum group-size rule | Present in the existing employer-cost and cost-per-head views; full dashboard verification pending |
| Official `unlock_PQ-09` validation | Unavailable in searched project folders |
| Invalid payroll rows confirmed with reasons | Pending authoritative evidence |
| Monthly totals fully reconciled | Pending; four months have recorded differences |
| Exclusion evidence and final reconciliation | Pending |

## 10. Final Status

**Task 9 is partially complete.**

The dashboard implementation and initial reconciliation documentation are available. Full completion requires verification of governed gross-pay and net-pay metrics, confirmation of the minimum-group-size and privacy rules in the dashboard code, evidence-based identification of invalid rows, and reconciliation of the four outstanding months—or a clear, supported explanation for each remaining difference.

The source payroll data has not been modified to force a match.

## 11. Payroll Exception Investigation — Four Candidate Records

Four payroll records were identified as reconciliation exception candidates. A controlled test excluding these four records produced matching payroll totals for all 18 months across employee count, gross pay, net pay and employer cost. This demonstrates reconciliation alignment, but does not independently prove that all four records are invalid.

### 11.1 Candidate Record Investigation

| Payroll Item ID | Month | Employee ID | Employee Key | Employee-Month Rows | Same-Run Rows | Finding |
|---|---|---|---:|---:|---:|---|
| PI-X0002 | May 2025 | EMP-6598 | 101421 | 1 | 1 | Employee mapped; no duplicate found |
| PI-X0004 | December 2025 | EMP-9002 | -1 | 1 | 1 | No employee dimension match |
| PI-X0001 | February 2026 | EMP-0194 | 100652 | 1 | 1 | Employee mapped; no duplicate found |
| PI-X0003 | April 2026 | EMP-9001 | -1 | 1 | 1 | No employee dimension match |

### 11.2 Investigation Conclusions

- **PI-X0003 and PI-X0004:** Confirmed employee-dimension mapping exceptions. Their employee keys are -1 and no matching employee dimension record was found. Source-owner review is required.
- **PI-X0001 and PI-X0002:** Both records are mapped and have one employee-month row and one same-run row. No duplicate-based exclusion reason was established.
- Matching reconciliation differences do not independently establish that a payroll record is invalid.
- No source payroll records were deleted or permanently modified.

### 11.3 Exclusion Decision

All four records were excluded only in a controlled reconciliation test. Permanent exclusion requires authoritative source validation and an approved business/data-quality rule.

The two mapping exceptions should not automatically be treated as invalid payroll payments. Their payroll validity and treatment in reporting require source-owner confirmation.

### 11.4 Reconciliation Evidence

The controlled test excluding the four candidate IDs matched the answer key for all 18 months across employee count, gross pay, net pay and employer cost.

This demonstrates reconciliation alignment, not independent proof of invalidity for all four records.

### 11.5 Status

Four candidate records investigated; two employee-mapping exceptions confirmed; two records remain unverified for exclusion purposes.

**The four-row invalid-record identification and justified exclusion requirement is not yet fully complete.**
