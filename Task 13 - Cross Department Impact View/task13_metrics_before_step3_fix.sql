
-- TASK 13 - STEP 3
-- Add overtime cost and leave days per head.
-- Grain: one row per department and month.

WITH
headcount_agg AS (
    SELECT
        department_id,
        month_start_date::timestamp::date AS month_start,
        MAX(headcount_start::numeric) AS headcount_start,
        MAX(headcount_end::numeric) AS headcount_end,
        MAX(attrition_rate_monthly_pct::numeric) AS attrition_rate_monthly_pct
    FROM fact_headcount_monthly
    WHERE month_start_date::timestamp::date >= DATE '2025-04-01'
    GROUP BY department_id, month_start_date::timestamp::date
),

payroll_agg AS (
    SELECT
        department_id,
        date_trunc('month', period_end_date::timestamp)::date AS month_start,
        SUM(gross_pay::numeric) AS gross_pay,
        SUM(net_pay::numeric) AS net_pay,
        SUM(employer_cost::numeric) AS employer_cost,
        SUM(overtime_pay::numeric) AS overtime_cost
    FROM fact_payroll
    GROUP BY department_id,
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
    GROUP BY department_id,
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
    GROUP BY l.leave_request_id, e.department_id, l.days
),

leave_agg AS (
    SELECT
        ld.department_id,
        date_trunc('month', d.date::timestamp)::date AS month_start,
        SUM(
            ld.recorded_leave_days /
            NULLIF(ld.total_working_days, 0)
        ) AS leave_days
    FROM leave_daily ld
    JOIN fact_leave l
        ON l.leave_request_id = ld.leave_request_id
    JOIN dim_date d
        ON d.date::timestamp::date
           BETWEEN l.start_date::timestamp::date
               AND l.end_date::timestamp::date
       AND d.is_working_day = 'Y'
    GROUP BY ld.department_id,
             date_trunc('month', d.date::timestamp)::date
),

combined AS (
    SELECT
        COALESCE(h.department_id, p.department_id,
                 a.department_id, l.department_id) AS department_id,
        COALESCE(h.month_start, p.month_start,
                 a.month_start, l.month_start) AS month_start,
        h.headcount_start,
        h.headcount_end,
        h.attrition_rate_monthly_pct,
        p.gross_pay,
        p.net_pay,
        p.employer_cost,
        p.overtime_cost,
        a.scheduled_days,
        a.present_days,
        a.overtime_hours,
        l.leave_days
    FROM headcount_agg h
    FULL OUTER JOIN payroll_agg p
        ON h.department_id = p.department_id
       AND h.month_start = p.month_start
    FULL OUTER JOIN attendance_agg a
        ON COALESCE(h.department_id, p.department_id) = a.department_id
       AND COALESCE(h.month_start, p.month_start) = a.month_start
    FULL OUTER JOIN leave_agg l
        ON COALESCE(h.department_id, p.department_id, a.department_id) = l.department_id
       AND COALESCE(h.month_start, p.month_start, a.month_start) = l.month_start
)

SELECT
    c.*,
    (c.headcount_start + c.headcount_end) / 2.0
        AS average_headcount,

    CASE
        WHEN (c.headcount_start + c.headcount_end) > 0
        THEN c.leave_days /
             NULLIF((c.headcount_start + c.headcount_end) / 2.0, 0)
        ELSE NULL
    END AS leave_days_per_head

FROM combined c
ORDER BY c.department_id, c.month_start;
