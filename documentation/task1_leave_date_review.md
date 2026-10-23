# Task 1 — Leave Date Exception Review

## Review outcome
Two rows in `fact_leave.csv` were quarantined because `end_date` precedes `start_date`.

| Leave Request ID | Start Date | End Date | Existing Status | Issue |
|---|---|---|---|---|
| LR-000025 | 2026-02-20 | 2026-02-19 | Rejected | End date precedes start date |
| LR-002286 | 2026-03-24 | 2026-03-23 | Approved | End date precedes start date |

## Disposition
- Preserve the original source data.
- Keep both invalid records quarantined until the source owner confirms the correct dates.
- Do not silently swap dates or alter approval status.
- The two exceptions remain a documented business-review item.

## Current pipeline evidence
The latest ETL run reports database load `SUCCESS`, with CSV row counts matching DuckDB for 32/32 tables. This does not mean the two invalid leave records have been corrected.
