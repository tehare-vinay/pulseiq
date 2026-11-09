SELECT
    team_id,
    sprint_id,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Done'
    ) AS done_tasks,
    SUM(
        CASE WHEN TRIM(status) = 'Done'
        THEN COALESCE(NULLIF(TRIM(story_points), ''), '0')::numeric
        ELSE 0 END
    ) AS completed_story_points,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Done'
          AND NULLIF(TRIM(started_date), '') IS NOT NULL
          AND NULLIF(TRIM(completed_date), '') IS NOT NULL
          AND TRIM(completed_date)::timestamp >= TRIM(started_date)::timestamp
    ) AS valid_cycle_time_tasks,
    ROUND(AVG(
        CASE WHEN TRIM(status) = 'Done'
          AND NULLIF(TRIM(started_date), '') IS NOT NULL
          AND NULLIF(TRIM(completed_date), '') IS NOT NULL
          AND TRIM(completed_date)::timestamp >= TRIM(started_date)::timestamp
        THEN EXTRACT(EPOCH FROM (
            TRIM(completed_date)::timestamp - TRIM(started_date)::timestamp
        )) / 86400.0
        END
    )::numeric, 2) AS avg_cycle_time_days,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Done'
          AND NULLIF(TRIM(completed_date), '') IS NOT NULL
          AND NULLIF(TRIM(due_date), '') IS NOT NULL
    ) AS eligible_on_time_tasks,
    COUNT(*) FILTER (
        WHERE TRIM(status) = 'Done'
          AND NULLIF(TRIM(completed_date), '') IS NOT NULL
          AND NULLIF(TRIM(due_date), '') IS NOT NULL
          AND TRIM(completed_date)::timestamp <= TRIM(due_date)::timestamp
    ) AS on_time_tasks,
    COUNT(*) FILTER (WHERE TRIM(status) = 'Cancelled') AS cancelled_tasks,
    COUNT(*) FILTER (WHERE TRIM(status) = 'Blocked') AS blocked_tasks,
    COUNT(*) FILTER (
        WHERE COALESCE(NULLIF(TRIM(reopened_count), ''), '0')::numeric > 0
    ) AS reopened_tasks,
    SUM(COALESCE(NULLIF(TRIM(reopened_count), ''), '0')::numeric)
        AS reopen_events
FROM public.fact_task
WHERE team_id IN ('T08', 'T10')
  AND sprint_id = 'SP-02'
GROUP BY team_id, sprint_id
ORDER BY team_id;
