WITH fact_history AS (
    SELECT
        'fact_payroll' AS source_table,
        f.payroll_item_id::text AS record_id,
        f.employee_id,
        f.employee_key,
        f.period_end_date::date AS period_end_date,
        d.valid_from,
        d.valid_to,
        CASE
            WHEN d.valid_from IS NOT NULL
             AND (date_trunc('month', f.period_end_date::date)
                  + interval '1 month - 1 day')::date < d.valid_from
                THEN TRUE
            WHEN d.valid_to IS NOT NULL
             AND date_trunc('month', f.period_end_date::date)::date > d.valid_to
                THEN TRUE
            ELSE FALSE
        END AS no_month_overlap
    FROM warehouse.fact_payroll f
    JOIN warehouse.dim_employee d
      ON d.employee_key = f.employee_key
    WHERE f.employee_key <> -1

    UNION ALL

    SELECT
        'fact_attendance_monthly',
        f.attendance_fact_id::text,
        f.employee_id,
        f.employee_key,
        f.period_end_date::date,
        d.valid_from,
        d.valid_to,
        CASE
            WHEN d.valid_from IS NOT NULL
             AND (date_trunc('month', f.period_end_date::date)
                  + interval '1 month - 1 day')::date < d.valid_from
                THEN TRUE
            WHEN d.valid_to IS NOT NULL
             AND date_trunc('month', f.period_end_date::date)::date > d.valid_to
                THEN TRUE
            ELSE FALSE
        END
    FROM warehouse.fact_attendance_monthly f
    JOIN warehouse.dim_employee d
      ON d.employee_key = f.employee_key
    WHERE f.employee_key <> -1
)
SELECT
    source_table,
    COUNT(*) AS non_unknown_rows,
    COUNT(*) FILTER (WHERE no_month_overlap) AS no_month_overlap_rows
FROM fact_history
GROUP BY source_table
ORDER BY source_table;

WITH attendance_review AS (
    SELECT
        f.attendance_fact_id,
        f.employee_id,
        f.employee_key,
        f.period_end_date::date AS period_end_date,
        d.valid_from,
        d.valid_to
    FROM warehouse.fact_attendance_monthly f
    JOIN warehouse.dim_employee d
      ON d.employee_key = f.employee_key
    WHERE f.employee_key <> -1
      AND (
          (d.valid_from IS NOT NULL
           AND (date_trunc('month', f.period_end_date::date)
                + interval '1 month - 1 day')::date < d.valid_from)
          OR
          (d.valid_to IS NOT NULL
           AND date_trunc('month', f.period_end_date::date)::date > d.valid_to)
      )
)
SELECT
    attendance_fact_id,
    employee_id,
    employee_key,
    period_end_date,
    valid_from,
    valid_to,
    'SOURCE REVIEW: fact month does not overlap linked employee version' AS review_reason
FROM attendance_review
ORDER BY attendance_fact_id;
