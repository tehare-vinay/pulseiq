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