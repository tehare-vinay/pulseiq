CREATE OR REPLACE VIEW public.metric_budget_payroll_dept_month AS
SELECT
    month::date AS month,
    department_id,
    NULLIF(TRIM(budget_payroll_cost), '')::numeric AS budget_payroll_cost
FROM public.budget_payroll_dept_month;

CREATE OR REPLACE VIEW public.metric_kpi_targets AS
SELECT
    month::date AS month,
    department_id,
    NULLIF(TRIM(attendance_rate_target), '')::numeric AS attendance_rate_target,
    NULLIF(TRIM(overtime_share_target_pct), '')::numeric AS overtime_share_target_pct,
    NULLIF(TRIM(attrition_monthly_target_pct), '')::numeric AS attrition_monthly_target_pct,
    NULLIF(TRIM(task_completion_target_pct), '')::numeric AS task_completion_target_pct
FROM public.kpi_targets;