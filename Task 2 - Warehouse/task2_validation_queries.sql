-- PulseIQ Task 2: three warehouse queries for validation.
-- Run: docker compose exec -T postgres psql -U pulseiq_user -d pulseiq_warehouse -v ON_ERROR_STOP=1 -f /app/sql/task2_validation_queries.sql

-- Q1. Monthly payroll totals by department. Compare monthly totals after summing departments
-- against reconciliation_answer_key.csv; compare department splits against payroll source.
SELECT to_char(period_end_date, 'YYYY-MM') AS month,
       attributes->>'department_id' AS department_id,
       COUNT(*) AS payroll_items,
       ROUND(SUM(gross_pay), 2) AS gross_pay,
       ROUND(SUM(net_pay), 2) AS net_pay,
       ROUND(SUM(employer_cost), 2) AS employer_cost
FROM warehouse.fact_payroll
WHERE payroll_item_id NOT IN ('PI-X0001', 'PI-X0002', 'PI-X0003', 'PI-X0004')
GROUP BY 1, 2
ORDER BY 1, 2;

-- Q2. Monthly headcount by department. Compare with clean fact_headcount_monthly.csv.
SELECT to_char(d.calendar_date, 'YYYY-MM') AS month,
       h.department_id,
       SUM(h.headcount_start) AS headcount_start,
       SUM(h.headcount_end) AS headcount_end,
       SUM(COALESCE(NULLIF(h.attributes->>'hires', '')::numeric, 0)) AS hires,
       SUM(COALESCE(NULLIF(h.attributes->>'exits', '')::numeric, 0)) AS exits
FROM warehouse.fact_headcount_monthly h
JOIN warehouse.dim_date d ON d.date_key = h.date_key
GROUP BY 1, 2
ORDER BY 1, 2;

-- Q3. Monthly attendance by department. Compare with clean fact_attendance_monthly.csv.
SELECT to_char(period_end_date, 'YYYY-MM') AS month,
       attributes->>'department_id' AS department_id,
       COUNT(*) AS employee_month_records,
       ROUND(AVG(NULLIF(attributes->>'attendance_rate', '')::numeric), 4) AS avg_attendance_rate,
       SUM(scheduled_days) AS scheduled_days,
       SUM(present_days) AS present_days,
       SUM(unpaid_absence_days) AS unpaid_absence_days
FROM warehouse.fact_attendance_monthly
GROUP BY 1, 2
ORDER BY 1, 2;
