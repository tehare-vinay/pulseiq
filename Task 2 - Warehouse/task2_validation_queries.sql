-- ============================================================
-- PulseIQ Analytics - Task 2: Warehouse Validation
-- PostgreSQL
-- ============================================================
-- Run from the project environment using the documented DB setup.
-- Compare the outputs against Task 1 clean data,
-- reconciliation_answer_key.csv, and documented exceptions.
-- Do not claim validation passed until results are reviewed.

SET search_path TO warehouse, public;

-- ------------------------------------------------------------
-- Q1. Monthly payroll totals by department
-- The four listed payroll IDs must be treated as exceptions
-- only when supported by the reconciliation evidence.
-- ------------------------------------------------------------

SELECT
    TO_CHAR(period_end_date, 'YYYY-MM') AS month,
    attributes->>'department_id' AS department_id,
    COUNT(*) AS payroll_rows,
    ROUND(SUM(gross_pay), 2) AS gross_pay,
    ROUND(SUM(net_pay), 2) AS net_pay,
    ROUND(SUM(employer_cost), 2) AS employer_cost
FROM warehouse.fact_payroll
WHERE payroll_item_id NOT IN
    ('PI-X0001', 'PI-X0002', 'PI-X0003', 'PI-X0004')
GROUP BY 1, 2
ORDER BY 1, 2;

-- Q1b. Review the excluded payroll records separately.

SELECT
    payroll_item_id,
    employee_id,
    employee_key,
    period_end_date,
    gross_pay,
    net_pay,
    employer_cost
FROM warehouse.fact_payroll
WHERE payroll_item_id IN
    ('PI-X0001', 'PI-X0002', 'PI-X0003', 'PI-X0004')
ORDER BY payroll_item_id;


-- ------------------------------------------------------------
-- Q2. Monthly headcount by department
-- Compare with clean fact_headcount_monthly.csv.
-- ------------------------------------------------------------

SELECT
    TO_CHAR(d.calendar_date, 'YYYY-MM') AS month,
    h.department_id,
    SUM(h.headcount_start) AS headcount_start,
    SUM(h.headcount_end) AS headcount_end,
    SUM(COALESCE(NULLIF(h.attributes->>'hires', '')::NUMERIC, 0))
        AS hires,
    SUM(COALESCE(NULLIF(h.attributes->>'exits', '')::NUMERIC, 0))
        AS exits
FROM warehouse.fact_headcount_monthly h
JOIN warehouse.dim_date d
    ON d.date_key = h.date_key
GROUP BY 1, 2
ORDER BY 1, 2;


-- ------------------------------------------------------------
-- Q3. Monthly attendance by department
-- Compare with clean fact_attendance_monthly.csv.
-- ------------------------------------------------------------

SELECT
    TO_CHAR(a.period_end_date, 'YYYY-MM') AS month,
    a.attributes->>'department_id' AS department_id,
    COUNT(*) AS employee_month_records,
    ROUND(
        AVG(NULLIF(a.attributes->>'attendance_rate', '')::NUMERIC),
        4
    ) AS avg_attendance_rate,
    SUM(a.scheduled_days) AS scheduled_days,
    SUM(a.present_days) AS present_days,
    SUM(a.unpaid_absence_days) AS unpaid_absence_days
FROM warehouse.fact_attendance_monthly a
GROUP BY 1, 2
ORDER BY 1, 2;


-- ------------------------------------------------------------
-- Q4. Orphan-key checks for declared foreign-key relationships
-- Expected result: zero rows for each relationship.
-- NULL optional foreign keys are not counted as orphans.
-- ------------------------------------------------------------

SELECT
    'fact_payroll.employee_key -> dim_employee.employee_key'
        AS relationship,
    COUNT(*) AS orphan_rows
FROM warehouse.fact_payroll f
LEFT JOIN warehouse.dim_employee d
    ON d.employee_key = f.employee_key
WHERE f.employee_key IS NOT NULL
  AND d.employee_key IS NULL

UNION ALL

SELECT
    'fact_payroll.date_key -> dim_date.date_key',
    COUNT(*)
FROM warehouse.fact_payroll f
LEFT JOIN warehouse.dim_date d
    ON d.date_key = f.date_key
WHERE f.date_key IS NOT NULL
  AND d.date_key IS NULL

UNION ALL

SELECT
    'fact_attendance_monthly.employee_key -> dim_employee.employee_key',
    COUNT(*)
FROM warehouse.fact_attendance_monthly f
LEFT JOIN warehouse.dim_employee d
    ON d.employee_key = f.employee_key
WHERE f.employee_key IS NOT NULL
  AND d.employee_key IS NULL

UNION ALL

SELECT
    'fact_leave.employee_key -> dim_employee.employee_key',
    COUNT(*)
FROM warehouse.fact_leave f
LEFT JOIN warehouse.dim_employee d
    ON d.employee_key = f.employee_key
WHERE f.employee_key IS NOT NULL
  AND d.employee_key IS NULL

UNION ALL

SELECT
    'fact_leave.leave_type_id -> dim_leave_type.leave_type_id',
    COUNT(*)
FROM warehouse.fact_leave f
LEFT JOIN warehouse.dim_leave_type d
    ON d.leave_type_id = f.leave_type_id
WHERE f.leave_type_id IS NOT NULL
  AND d.leave_type_id IS NULL

UNION ALL

SELECT
    'fact_headcount_monthly.date_key -> dim_date.date_key',
    COUNT(*)
FROM warehouse.fact_headcount_monthly f
LEFT JOIN warehouse.dim_date d
    ON d.date_key = f.date_key
WHERE d.date_key IS NULL

UNION ALL

SELECT
    'fact_headcount_monthly.department_id -> dim_department.department_id',
    COUNT(*)
FROM warehouse.fact_headcount_monthly f
LEFT JOIN warehouse.dim_department d
    ON d.department_id = f.department_id
WHERE d.department_id IS NULL

ORDER BY 1;


-- ------------------------------------------------------------
-- Q5. Warehouse row counts for Task 1 reconciliation
-- Compare with accepted/clean source counts and documented
-- quarantine or exception records.
-- ------------------------------------------------------------

SELECT 'dim_employee' AS table_name, COUNT(*) AS row_count
FROM warehouse.dim_employee

UNION ALL

SELECT 'dim_department', COUNT(*)
FROM warehouse.dim_department

UNION ALL

SELECT 'dim_role', COUNT(*)
FROM warehouse.dim_role

UNION ALL

SELECT 'dim_date', COUNT(*)
FROM warehouse.dim_date

UNION ALL

SELECT 'dim_leave_type', COUNT(*)
FROM warehouse.dim_leave_type

UNION ALL

SELECT 'fact_payroll', COUNT(*)
FROM warehouse.fact_payroll

UNION ALL

SELECT 'fact_attendance_monthly', COUNT(*)
FROM warehouse.fact_attendance_monthly

UNION ALL

SELECT 'fact_leave', COUNT(*)
FROM warehouse.fact_leave

UNION ALL

SELECT 'fact_headcount_monthly', COUNT(*)
FROM warehouse.fact_headcount_monthly

ORDER BY 1;
