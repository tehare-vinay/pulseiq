CREATE OR REPLACE VIEW public.metric_m13_attendance_rate AS
SELECT
    period_end_date,
    department_id,
    ROUND(
        100.0 * SUM(
            COALESCE(NULLIF(TRIM(present_days), '')::numeric, 0)
            + 0.5 * CASE
                WHEN TRIM(COALESCE(half_days_unpaid, '')) ~ '^[0-9]+(\.[0-9]+)?$'
                THEN TRIM(half_days_unpaid)::numeric
                ELSE 0
            END
        ) / NULLIF(
            SUM(NULLIF(TRIM(scheduled_days), '')::numeric),
            0
        ),
        2
    ) AS attendance_rate_pct
FROM public.fact_attendance_monthly
GROUP BY period_end_date, department_id
HAVING COUNT(DISTINCT employee_id) >= 5;
