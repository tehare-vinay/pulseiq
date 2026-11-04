-- TASK 13 - STEP 3 FINAL CORRECTED DATASET
-- Reporting period: 2025-04-01 through 2026-09-30.
-- Grain: one row per department and month.
-- Each source is aggregated independently before joining.
-- Leave days are allocated to the calendar month of each approved working leave date.

WITH
headcount_agg AS (
    SELECT
        department_id,
        month_start_date::timestamp::date AS month_start,
        MAX(headcount_start::numeric) AS headcount_start,
        MAX(headcount_end::numeric) AS headcount_end,
        MAX(hires::numeric) AS hires,
        MAX(exits::numeric) AS exits,
        MAX(voluntary_exits::numeric) AS voluntary_exits,
        MAX(attrition_rate_monthly_pct::numeric) AS attrition_rate_monthly_pct
    FROM fact_headcount_monthly
    WHERE month_start_date::timestamp::date >= DATE '2025-04-01'
      AND month_start_date::timestamp::date < DATE '2026-10-01'
    GROUP BY department_id, month_start_date::timestamp::date
),
payroll_agg AS (
    SELECT
        department_id,
        date_trunc('month', period_end_date::timestamp)::date AS month_start,
        SUM(gross_pay::numeric) AS gross_pay,
        SUM(net_pay::numeric) AS net_pay,
        SUM(employer_cost::numeric) AS employer_cost,
        SUM(overtime_pay::numeric) AS overtime_cost,
        SUM(overtime_hours_paid::numeric) AS overtime_hours_paid
    FROM fact_payroll
    WHERE period_end_date::timestamp >= TIMESTAMP '2025-04-01'
      AND period_end_date::timestamp < TIMESTAMP '2026-10-01'
    GROUP BY department_id, date_trunc('month', period_end_date::timestamp)::date
),
attendance_agg AS (
    SELECT
        department_id,
        date_trunc('month', period_end_date::timestamp)::date AS month_start,
        SUM(scheduled_days::numeric) AS scheduled_days,
        SUM(present_days::numeric) AS present_days,
        SUM(overtime_hours::numeric) AS overtime_hours
    FROM fact_attendance_monthly
    WHERE period_end_date::timestamp >= TIMESTAMP '2025-04-01'
      AND period_end_date::timestamp < TIMESTAMP '2026-10-01'
    GROUP BY department_id, date_trunc('month', period_end_date::timestamp)::date
),
leave_agg AS (
    SELECT
        e.department_id,
        date_trunc('month', d.date::timestamp)::date AS month_start,
        COUNT(*)::numeric AS leave_days
    FROM fact_leave l
    JOIN dim_employee e
      ON l.employee_key = e.employee_key
    JOIN dim_date d
      ON d.date::timestamp::date BETWEEN l.start_date::timestamp::date
                                     AND l.end_date::timestamp::date
    WHERE l.status = 'Approved'
      AND d.is_working_day = 'Y'
      AND d.date::timestamp::date >= DATE '2025-04-01'
      AND d.date::timestamp::date < DATE '2026-10-01'
    GROUP BY e.department_id, date_trunc('month', d.date::timestamp)::date
),
all_keys AS (
    SELECT department_id, month_start FROM headcount_agg
    UNION
    SELECT department_id, month_start FROM payroll_agg
    UNION
    SELECT department_id, month_start FROM attendance_agg
    UNION
    SELECT department_id, month_start FROM leave_agg
),
combined AS (
    SELECT
        k.department_id,
        k.month_start,
        h.headcount_start,
        h.headcount_end,
        h.hires,
        h.exits,
        h.voluntary_exits,
        h.attrition_rate_monthly_pct,
        p.gross_pay,
        p.net_pay,
        p.employer_cost,
        p.overtime_cost,
        p.overtime_hours_paid,
        a.scheduled_days,
        a.present_days,
        a.overtime_hours,
        l.leave_days,
        CASE WHEN h.department_id IS NOT NULL THEN 1 ELSE 0 END AS has_headcount,
        CASE WHEN p.department_id IS NOT NULL THEN 1 ELSE 0 END AS has_payroll,
        CASE WHEN a.department_id IS NOT NULL THEN 1 ELSE 0 END AS has_attendance,
        CASE WHEN l.department_id IS NOT NULL THEN 1 ELSE 0 END AS has_leave
    FROM all_keys k
    LEFT JOIN headcount_agg h
      ON h.department_id = k.department_id AND h.month_start = k.month_start
    LEFT JOIN payroll_agg p
      ON p.department_id = k.department_id AND p.month_start = k.month_start
    LEFT JOIN attendance_agg a
      ON a.department_id = k.department_id AND a.month_start = k.month_start
    LEFT JOIN leave_agg l
      ON l.department_id = k.department_id AND l.month_start = k.month_start
)
SELECT
    c.*,
    (c.headcount_start + c.headcount_end) / 2.0 AS average_headcount,
    c.leave_days / NULLIF((c.headcount_start + c.headcount_end) / 2.0, 0)
        AS leave_days_per_head,
    COUNT(*) OVER (PARTITION BY c.department_id, c.month_start)
        AS department_month_key_count
FROM combined c
ORDER BY c.department_id, c.month_start;

-- Expected validation for the reference window:
-- 1) no duplicate department_id + month_start keys
-- 2) dates begin 2025-04-01 and end 2026-09-01
-- 3) overtime_cost reconciles to SUM(fact_payroll.overtime_pay)
-- 4) leave_days_per_head = leave_days / average_headcount
