WITH payroll_monthly AS (
    SELECT
        department_id,
        date_trunc('month', period_end_date::timestamp)::date AS month_start,
        SUM(employer_cost::numeric) AS employer_cost,
        SUM(overtime_pay::numeric) AS overtime_cost
    FROM fact_payroll
    WHERE date_trunc('month', period_end_date::timestamp)::date >= DATE '2025-04-01'
    GROUP BY department_id,
             date_trunc('month', period_end_date::timestamp)::date
),
headcount_monthly AS (
    SELECT
        department_id,
        month_start_date::timestamp::date AS month_start,
        MAX(attrition_rate_monthly_pct::numeric) AS attrition_rate_monthly_pct
    FROM fact_headcount_monthly
    WHERE month_start_date::timestamp::date >= DATE '2025-04-01'
    GROUP BY department_id, month_start_date::timestamp::date
),
monthly_comparison AS (
    SELECT
        h.department_id,
        h.month_start,
        p.employer_cost,
        p.overtime_cost,
        h.attrition_rate_monthly_pct
    FROM headcount_monthly h
    INNER JOIN payroll_monthly p
        ON p.department_id = h.department_id
       AND p.month_start = h.month_start
)
SELECT
    d.department_id,
    d.department_name,
    COUNT(*) AS months_compared,
    ROUND(SUM(m.employer_cost), 2) AS total_employer_cost,
    ROUND(SUM(m.overtime_cost), 2) AS total_overtime_cost,
    ROUND(AVG(m.attrition_rate_monthly_pct), 2) AS avg_monthly_attrition_pct
FROM monthly_comparison m
JOIN dim_department d
    ON d.department_id = m.department_id
GROUP BY d.department_id, d.department_name
ORDER BY d.department_id;
