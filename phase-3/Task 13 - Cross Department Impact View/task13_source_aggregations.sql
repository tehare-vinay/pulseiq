-- TASK 13: Step 2 - Source-wise aggregation
-- Target grain: one row per department and month.
-- Reporting period: April 2025 to September 2026.
-- Each source is aggregated independently before joining.

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
    GROUP BY
        department_id,
        date_trunc('month', period_end_date::timestamp)::date
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
    GROUP BY
        department_id,
        date_trunc('month', period_end_date::timestamp)::date
),

leave_daily AS (
    SELECT
        l.leave_request_id,
        e.department_id,
        l.days::numeric AS recorded_leave_days,
        COUNT(*) FILTER (
            WHERE d.is_working_day = 'Y'
        ) AS total_working_days
    FROM fact_leave l
    JOIN dim_employee e
        ON l.employee_key = e.employee_key
    JOIN dim_date d
        ON d.date::timestamp::date
           BETWEEN l.start_date::timestamp::date
               AND l.end_date::timestamp::date
    WHERE l.status = 'Approved'
      AND l.end_date::timestamp::date >= DATE '2025-04-01'
      AND l.start_date::timestamp::date < DATE '2026-10-01'
    GROUP BY
        l.leave_request_id,
        e.department_id,
        l.days
),

leave_agg AS (
    SELECT
        e.department_id,
        date_trunc('month', d.date::timestamp)::date AS month_start,
        SUM(
            ld.recorded_leave_days /
            NULLIF(ld.total_working_days, 0)
        ) AS leave_days
    FROM fact_leave l
    JOIN dim_employee e
        ON l.employee_key = e.employee_key
    JOIN leave_daily ld
        ON ld.leave_request_id = l.leave_request_id
    JOIN dim_date d
        ON d.date::timestamp::date
           BETWEEN l.start_date::timestamp::date
               AND l.end_date::timestamp::date
       AND d.is_working_day = 'Y'
    WHERE l.status = 'Approved'
      AND d.date::timestamp::date >= DATE '2025-04-01'
      AND d.date::timestamp::date < DATE '2026-10-01'
    GROUP BY
        e.department_id,
        date_trunc('month', d.date::timestamp)::date
)

SELECT 'HEADCOUNT' AS source, department_id, month_start,
       headcount_start AS metric_1, headcount_end AS metric_2,
       hires AS metric_3, exits AS metric_4,
       voluntary_exits AS metric_5,
       attrition_rate_monthly_pct AS metric_6
FROM headcount_agg

UNION ALL

SELECT 'PAYROLL', department_id, month_start,
       gross_pay, net_pay, employer_cost,
       overtime_cost, overtime_hours_paid, NULL::numeric
FROM payroll_agg

UNION ALL

SELECT 'ATTENDANCE', department_id, month_start,
       scheduled_days, present_days, overtime_hours,
       NULL::numeric, NULL::numeric, NULL::numeric
FROM attendance_agg

UNION ALL

SELECT 'LEAVE', department_id, month_start,
       leave_days, NULL::numeric, NULL::numeric,
       NULL::numeric, NULL::numeric, NULL::numeric
FROM leave_agg

ORDER BY source, department_id, month_start;
