-- Task 6: Governed monthly overtime hours
CREATE OR REPLACE VIEW public.metric_m32_overtime_hours AS
SELECT
    period_end_date,
    department_id,
    SUM(NULLIF(TRIM(overtime_hours), '')::numeric) AS overtime_hours
FROM public.fact_attendance_monthly
GROUP BY period_end_date, department_id
HAVING COUNT(DISTINCT NULLIF(TRIM(employee_id), '')) >= 5;

COMMENT ON VIEW public.metric_m32_overtime_hours IS
'Task 6 governed monthly department overtime hours. Groups with fewer than five distinct employees are excluded.';

-- Task 6: Leave requests and days by month, leave type and status
CREATE OR REPLACE VIEW public.metric_m33_leave_days_by_type_status AS
SELECT
    LEFT(NULLIF(TRIM(start_date), ''), 7) AS leave_month,
    leave_type_code,
    status,
    COUNT(*) AS leave_requests,
    COUNT(DISTINCT NULLIF(TRIM(employee_id), '')) AS employee_count,
    SUM(NULLIF(TRIM(days), '')::numeric) AS leave_days
FROM public.fact_leave
WHERE NULLIF(TRIM(start_date), '') IS NOT NULL
GROUP BY
    LEFT(NULLIF(TRIM(start_date), ''), 7),
    leave_type_code,
    status
HAVING COUNT(DISTINCT NULLIF(TRIM(employee_id), '')) >= 5;

COMMENT ON VIEW public.metric_m33_leave_days_by_type_status IS
'Task 6 governed monthly leave request and leave day totals by leave type and status. Groups with fewer than five distinct employees are excluded.';
