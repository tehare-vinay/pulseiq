-- Task 7: Voluntary vs Other Exits
-- Publish only when the split is supported by the source data.
-- Do not infer other exits when the source totals do not reconcile.

CREATE OR REPLACE VIEW public.metric_m07_exit_type_split AS
WITH monthly AS (
    SELECT
        month_start_date,
        SUM(NULLIF(TRIM(headcount_start), '')::numeric)
            AS headcount_start,
        SUM(NULLIF(TRIM(headcount_end), '')::numeric)
            AS headcount_end,
        SUM(NULLIF(TRIM(exits), '')::numeric)
            AS total_exits,
        SUM(NULLIF(TRIM(voluntary_exits), '')::numeric)
            AS voluntary_exits
    FROM public.fact_headcount_monthly
    GROUP BY month_start_date
),
split AS (
    SELECT
        month_start_date,
        headcount_start,
        headcount_end,
        total_exits,
        voluntary_exits,
        total_exits - voluntary_exits AS other_exits
    FROM monthly
)
SELECT
    month_start_date,
    'ALL_DEPARTMENTS'::text AS department_id,
    total_exits,
    voluntary_exits,
    other_exits
FROM split
WHERE headcount_start >= 10
  AND headcount_end >= 10
  AND total_exits >= 5
  AND voluntary_exits >= 0
  AND voluntary_exits <= total_exits
  AND other_exits >= 0;
