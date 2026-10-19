# PulseIQ Task 1 — Data handling decisions

- **Input scope:** Process only CSV exports with the official PulseIQ dataset filename prefix. Ignore the README export and `fact_payroll(1).csv`, which is a duplicate export of `fact_payroll.csv`; this avoids double-counting the same payroll fact.
- **Raw-data protection:** The ETL reads raw CSVs but never overwrites or deletes them.
- **Duplicate policy:** Trim surrounding text whitespace first, then remove exact duplicate rows only. Write removed rows to `data/rejected/rejected_rows.csv` with the source filename and reason. Do not delete rows merely because a business key repeats; payroll and employee-history tables can contain legitimate repeated employee IDs.
- **Missing values:** Blank strings become missing values. No salary, attendance, leave, or other business value is imputed without an explicit rule in `data_contracts.csv`.
- **Date parsing:** Parse recognizable date columns only when all nonblank values parse. If parsing would lose a source value, retain that column as supplied and log the issue for review.
- **Tenure reference date:** Use 2026-09-30, the documented end of the fact-data period, rather than today's date or the calendar dimension's later maximum date. This keeps `tenure_days` repeatable between runs.
- **Hire/exit date conflict:** Do not silently swap dates or delete a row when `hire_date` is after `exit_date`. Preserve the record and report it for review because the correct fix requires confirmation of the employee's history/business record.
- **SCD Type 2 employee history:** `employee_key` is the unique version key. `employee_id` may legitimately appear on multiple history versions, so it is not treated as globally unique in `dim_employee`. Join fact tables to the employee dimension using `employee_key`.
- **Salary validation:** Negative `gross_pay`, `net_pay`, or `employer_cost` values are validation issues, not automatically changed to zero. Keep salary outputs restricted and use aggregate reporting only.
- **Repeatability:** Clean files are overwritten from the same raw inputs each run; the rejected-row file and current validation report describe that run. `etl_run_log.csv` is append-only history.
- **Metrics:** `documentation/metric_dictionary_phase1.csv` contains the first five rows from the official `metric_dictionary.csv`; definitions and formulas are not invented by the ETL.
### Known Issue: Payroll Orphan Foreign Keys

The source dataset intentionally contains two payroll records, `PI-X0003` and `PI-X0004`, with `employee_key = -1` and employee IDs `EMP-9001` and `EMP-9002` that are absent from `dim_employee`.

These records are documented in `dq_known_issues.csv` as issue `DQ-03` (`ORPHAN_FOREIGN_KEY`). Preserve the original records in raw data, flag them in data-quality validation, and do not silently replace the employee keys or delete the source records.

### Data Quality Exception: Placeholder Employee Keys

**Table:** `fact_payroll`

**Affected records:** `PI-X0003` and `PI-X0004`

**Issue:** These two payroll records use `employee_key = -1`, which does not match a valid employee record in `dim_employee`.

**Handling decision:** Retain the original records and flag them for investigation. Do not assign a replacement employee key or delete the payroll records without confirmation from the data owner. The placeholder may represent an unknown or unmatched employee.

**Validation result:** 2 sentinel/orphan records; 0 missing employee keys; status `REVIEW`.

**Reason:** This preserves payroll traceability and prevents unsupported changes to financial data. The exception should be resolved only after the data contract or data owner confirms the intended mapping.

## Official Metric Dictionary — First 5 Metrics

Source: `metric_dictionary.csv`

### M01 — Headcount
- **Definition:** Active employees on the last day of the month (permanent and contract).
- **Formula:** `COUNT(DISTINCT employee_id)` with `hire_date <= month_end` AND `(exit_date IS NULL OR exit_date > month_end)`
- **Source tables:** `fact_headcount_monthly / dim_employee`
- **Grain:** Department
- **Time period:** Month end
- **Unit:** Count
- **Caveat:** Excludes CEO if you compare departments only.
- **Minimum group size:** 5

### M02 — Hires
- **Definition:** Employees whose `hire_date` falls in the month.
- **Formula:** `COUNT(employee_id)` where `hire_date` is in month.
- **Source table:** `fact_headcount_monthly`
- **Grain:** Department × month
- **Time period:** Month
- **Unit:** Count
- **Caveat:** Transfers are not hires.
- **Minimum group size:** 5

### M03 — Exits
- **Definition:** Employees whose `exit_date` falls in the month (resigned, terminated or contract ended).
- **Formula:** `COUNT(employee_id)` where `exit_date` is in month.
- **Source table:** `fact_headcount_monthly`
- **Grain:** Department × month
- **Time period:** Month
- **Unit:** Count
- **Good direction:** Lower is better
- **Minimum group size:** 5

### M04 — Attrition rate (monthly)
- **Definition:** Share of people who left in the month.
- **Formula:** `Exits / headcount_start × 100`
- **Source table:** `fact_headcount_monthly`
- **Grain:** Department × month
- **Time period:** Month
- **Unit:** Percent
- **Good direction:** Lower is better
- **Caveat:** Very noisy for small departments.
- **Minimum group size:** 10

### M05 — Attrition rate (rolling 12 months)
- **Definition:** Leavers in the last 12 months divided by average headcount over the same months.
- **Formula:** `SUM(exits, 12m) / AVG(headcount_end, 12m) × 100`
- **Source table:** `fact_headcount_monthly`
- **Grain:** Department × month
- **Time period:** 12 months
- **Unit:** Percent
- **Good direction:** Lower is better
- **Caveat:** Use for headline reporting; monthly is too noisy.
- **Minimum group size:** 10

### Payroll Placeholder Employee Keys

Two payroll records contain `employee_key = -1`, which represents an unresolved or placeholder employee reference. These records must not be mapped to an arbitrary employee or deleted automatically. They should be flagged for review and excluded from employee-level analysis until the data owner confirms the correct mapping. Original source records must remain unchanged.

### Placeholder Employee Keys in Payroll

Two payroll records (`PI-X0003` and `PI-X0004`) contain `employee_key = -1`, which does not match a valid employee record in `dim_employee`.

**Decision:** Retain both records in the source and clean CSV files, flag them for review, and exclude them from employee-level analysis until the data owner confirms the correct mapping. Do not automatically replace the placeholder key or delete these records.

**Reason:** Automatic correction could assign payroll amounts to the wrong employee and produce inaccurate reporting. The issue is recorded as a review item in the Phase 1 validation report.