CREATE OR REPLACE VIEW public.metric_m26_task_health AS
SELECT
    team_id,
    sprint_id,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Cancelled'
    ) AS cancelled_tasks,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Blocked'
    ) AS blocked_tasks,
    COUNT(*) FILTER (
        WHERE COALESCE(
            NULLIF(TRIM(reopened_count), '')::numeric, 0
        ) > 0
    ) AS reopened_tasks,
    COALESCE(
        SUM(COALESCE(NULLIF(TRIM(reopened_count), '')::numeric, 0)),
        0
    ) AS reopen_events
FROM public.fact_task
GROUP BY team_id, sprint_id;
