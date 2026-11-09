-- PulseIQ Task 2: SCD Type 2 history validation for monthly facts.
-- Run from project root:
-- docker compose exec -T postgres psql -U pulseiq_user -d pulseiq_warehouse -v ON_ERROR_STOP=1 -f /app/sql/task2_employee_history_validation.sql
-- Monthly fact dates are period_end_date, but employees can exit/change history mid-month.
-- Validate whether the linked employee_key version overlaps the fact month, not whether
-- valid_to is >= month-end. Never remap a key merely to make a check pass.

WITH fact_rows AS (
    SELECT 'fact_payroll'::text AS source_table, f.payroll_item_id::text AS record_id,
           f.employee_id, f.employee_key, f.period_end_date,
           NULLIF(f.attributes->>'department_id','') AS fact_department_id
    FROM warehouse.fact_payroll f
    UNION ALL
    SELECT 'fact_attendance_monthly', f.attendance_fact_id::text,
           f.employee_id, f.employee_key, f.period_end_date,
           NULLIF(f.attributes->>'department_id','')
    FROM warehouse.fact_attendance_monthly f
), checked AS (
    SELECT f.*, d.employee_id AS dimension_employee_id,
           d.department_id AS dimension_department_id,
           d.valid_from, d.valid_to,
           (COALESCE(d.valid_from, DATE '0001-01-01') <= (date_trunc('month', f.period_end_date)::date + INTERVAL '1 month - 1 day')::date
            AND COALESCE(d.valid_to, DATE '9999-12-31') >= date_trunc('month', f.period_end_date)::date) AS version_overlaps_month
    FROM fact_rows f
    LEFT JOIN warehouse.dim_employee d ON d.employee_key = f.employee_key
    WHERE f.employee_key <> -1
)
SELECT source_table,
       COUNT(*) AS non_unknown_rows,
       COUNT(*) FILTER (WHERE dimension_employee_id IS NULL) AS missing_dimension_key_rows,
       COUNT(*) FILTER (WHERE dimension_employee_id IS NOT NULL AND employee_id IS DISTINCT FROM dimension_employee_id) AS employee_id_mismatch_rows,
       COUNT(*) FILTER (WHERE dimension_employee_id IS NOT NULL AND fact_department_id IS DISTINCT FROM dimension_department_id) AS department_mismatch_rows,
       COUNT(*) FILTER (WHERE dimension_employee_id IS NOT NULL AND NOT version_overlaps_month) AS no_employee_version_overlaps_fact_month
FROM checked
GROUP BY source_table
ORDER BY source_table;

-- These are the expected source exceptions: monthly attendance after the linked employee's
-- final validity month. Keep them in the fact table for row-count traceability, but flag them
-- for source/business review. Do not invent a replacement employee_key.
WITH f AS (
    SELECT a.attendance_fact_id, a.employee_id, a.employee_key, a.period_end_date,
           NULLIF(a.attributes->>'department_id','') AS fact_department_id
    FROM warehouse.fact_attendance_monthly a
), x AS (
    SELECT f.*, d.valid_from, d.valid_to, d.department_id AS dimension_department_id,
           d.exit_date,
           (COALESCE(d.valid_from, DATE '0001-01-01') <= (date_trunc('month', f.period_end_date)::date + INTERVAL '1 month - 1 day')::date
            AND COALESCE(d.valid_to, DATE '9999-12-31') >= date_trunc('month', f.period_end_date)::date) AS version_overlaps_month
    FROM f JOIN warehouse.dim_employee d ON d.employee_key = f.employee_key
    WHERE f.employee_key <> -1
)
SELECT attendance_fact_id, employee_id, employee_key, period_end_date,
       valid_from, valid_to, exit_date, fact_department_id, dimension_department_id,
       'REVIEW: attendance month falls after linked employee version ended; no key remap without source confirmation' AS review_reason
FROM x
WHERE NOT version_overlaps_month
ORDER BY period_end_date, employee_id;
