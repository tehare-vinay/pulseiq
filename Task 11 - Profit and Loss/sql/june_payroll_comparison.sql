-- Task 11: June 2026 payroll audit
-- Remove thousands separators before numeric conversion.

-- A. Payroll totals
SELECT
    COUNT(*) AS payroll_rows,
    COUNT(DISTINCT run_id) AS payroll_runs,

    ROUND(SUM(NULLIF(REPLACE(TRIM(gross_pay), ',', ''), '')::numeric), 2)
        AS gross_pay,

    ROUND(SUM(NULLIF(REPLACE(TRIM(pf_employer), ',', ''), '')::numeric), 2)
        AS pf_employer,

    ROUND(SUM(NULLIF(REPLACE(TRIM(esi_employer), ',', ''), '')::numeric), 2)
        AS esi_employer,

    ROUND(SUM(NULLIF(REPLACE(TRIM(employer_cost), ',', ''), '')::numeric), 2)
        AS employer_cost

FROM fact_payroll
WHERE period_end_date::date >= DATE '2026-06-01'
  AND period_end_date::date < DATE '2026-07-01';


-- B. Payroll totals by run
SELECT
    run_id,
    COUNT(*) AS employee_rows,

    ROUND(SUM(NULLIF(REPLACE(TRIM(gross_pay), ',', ''), '')::numeric), 2)
        AS gross_pay,

    ROUND(SUM(NULLIF(REPLACE(TRIM(pf_employer), ',', ''), '')::numeric), 2)
        AS pf_employer,

    ROUND(SUM(NULLIF(REPLACE(TRIM(esi_employer), ',', ''), '')::numeric), 2)
        AS esi_employer,

    ROUND(SUM(NULLIF(REPLACE(TRIM(employer_cost), ',', ''), '')::numeric), 2)
        AS employer_cost

FROM fact_payroll
WHERE period_end_date::date >= DATE '2026-06-01'
  AND period_end_date::date < DATE '2026-07-01'
GROUP BY run_id
ORDER BY run_id;


-- Find actual payroll metric view names
SELECT
    schemaname,
    viewname
FROM pg_views
WHERE viewname ILIKE '%payroll%'
ORDER BY schemaname, viewname;
