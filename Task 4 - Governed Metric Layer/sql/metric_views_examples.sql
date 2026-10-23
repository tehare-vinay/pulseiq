CREATE OR REPLACE VIEW public.metric_m01_headcount AS 
 SELECT month_start_date,
    department_id,
    sum((NULLIF(headcount_end, ''::text))::numeric) AS headcount
   FROM fact_headcount_monthly
  GROUP BY month_start_date, department_id
 HAVING (sum((NULLIF(headcount_end, ''::text))::numeric) >= (5)::numeric);

CREATE OR REPLACE VIEW public.metric_m02_hires AS 
 SELECT month_start_date,
    department_id,
        CASE
            WHEN (sum((NULLIF(hires, ''::text))::numeric) >= (5)::numeric) THEN sum((NULLIF(hires, ''::text))::numeric)
            ELSE NULL::numeric
        END AS hires
   FROM fact_headcount_monthly
  GROUP BY month_start_date, department_id
 HAVING (sum((NULLIF(headcount_end, ''::text))::numeric) >= (5)::numeric);

CREATE OR REPLACE VIEW public.metric_m03_exits AS 
 SELECT month_start_date,
    department_id,
        CASE
            WHEN (sum((NULLIF(exits, ''::text))::numeric) >= (5)::numeric) THEN sum((NULLIF(exits, ''::text))::numeric)
            ELSE NULL::numeric
        END AS exits
   FROM fact_headcount_monthly
  GROUP BY month_start_date, department_id
 HAVING (sum((NULLIF(headcount_end, ''::text))::numeric) >= (5)::numeric);

CREATE OR REPLACE VIEW public.metric_m04_attrition_rate AS 
 SELECT month_start_date,
    department_id,
        CASE
            WHEN (count(*) FILTER (WHERE ((COALESCE(NULLIF(headcount_start, ''::text), '0'::text))::numeric > (0)::numeric)) = 0) THEN NULL::numeric
            ELSE round(((100.0 * sum((COALESCE(NULLIF(exits, ''::text), '0'::text))::numeric)) / NULLIF(sum((COALESCE(NULLIF(headcount_start, ''::text), '0'::text))::numeric), (0)::numeric)), 2)
        END AS attrition_rate_pct
   FROM fact_headcount_monthly
  GROUP BY month_start_date, department_id
 HAVING (sum((COALESCE(NULLIF(headcount_start, ''::text), '0'::text))::numeric) >= (10)::numeric);

CREATE OR REPLACE VIEW public.metric_m05_rolling_12m_attrition AS 
 WITH monthly AS (
         SELECT (fact_headcount_monthly.month_start_date)::timestamp without time zone AS month_start_date,
            fact_headcount_monthly.department_id,
            sum((COALESCE(NULLIF(fact_headcount_monthly.exits, ''::text), '0'::text))::numeric) AS exits,
            sum((COALESCE(NULLIF(fact_headcount_monthly.headcount_start, ''::text), '0'::text))::numeric) AS headcount_start
           FROM fact_headcount_monthly
          GROUP BY (fact_headcount_monthly.month_start_date)::timestamp without time zone, fact_headcount_monthly.department_id
        ), rolling AS (
         SELECT monthly.month_start_date,
            monthly.department_id,
            sum(monthly.exits) OVER (PARTITION BY monthly.department_id ORDER BY monthly.month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS exits_12m,
            avg(monthly.headcount_start) OVER (PARTITION BY monthly.department_id ORDER BY monthly.month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS avg_headcount_12m,
            count(*) OVER (PARTITION BY monthly.department_id ORDER BY monthly.month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS months_available
           FROM monthly
        )
 SELECT month_start_date,
    department_id,
        CASE
            WHEN (months_available = 12) THEN round(((100.0 * exits_12m) / NULLIF(avg_headcount_12m, (0)::numeric)), 2)
            ELSE NULL::numeric
        END AS rolling_12m_attrition_pct
   FROM rolling
  WHERE (avg_headcount_12m >= (10)::numeric);

CREATE OR REPLACE VIEW public.metric_m06_voluntary_attrition AS 
 SELECT month_start_date,
    department_id,
    sum((COALESCE(NULLIF(voluntary_exits, ''::text), '0'::text))::numeric) AS voluntary_exits
   FROM fact_headcount_monthly
  GROUP BY month_start_date, department_id
 HAVING (sum((COALESCE(NULLIF(headcount_start, ''::text), '0'::text))::numeric) >= (10)::numeric);

CREATE OR REPLACE VIEW public.metric_m07_gross_pay AS 
 SELECT period_end_date,
    department_id,
    sum((NULLIF(gross_pay, ''::text))::numeric) AS gross_pay
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m08_net_pay AS 
 SELECT period_end_date,
    department_id,
    sum((NULLIF(net_pay, ''::text))::numeric) AS net_pay
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m09_payroll_cost AS 
 SELECT period_end_date,
    department_id,
    sum((NULLIF(employer_cost, ''::text))::numeric) AS employer_cost
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m10_cost_per_head AS 
 SELECT period_end_date,
    department_id,
    (sum((NULLIF(employer_cost, ''::text))::numeric) / (NULLIF(count(DISTINCT employee_id), 0))::numeric) AS cost_per_head
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m11_overtime_share AS 
 SELECT period_end_date,
    department_id,
    ((100.0 * sum((NULLIF(overtime_pay, ''::text))::numeric)) / NULLIF(sum((NULLIF(employer_cost, ''::text))::numeric), (0)::numeric)) AS overtime_share_pct
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m12_variable_pay_share AS 
 SELECT period_end_date,
    department_id,
    ((100.0 * sum((NULLIF(variable_pay, ''::text))::numeric)) / NULLIF(sum((NULLIF(gross_pay, ''::text))::numeric), (0)::numeric)) AS variable_pay_share_pct
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m13_attendance_rate AS 
 SELECT period_end_date,
    department_id,
    ((100.0 * sum((NULLIF(present_days, ''::text))::numeric)) / NULLIF(sum((NULLIF(scheduled_days, ''::text))::numeric), (0)::numeric)) AS attendance_rate_pct
   FROM fact_attendance_monthly
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m14_late_arrival_rate AS 
 SELECT period_end_date,
    department_id,
    ((100.0 * sum((NULLIF(late_arrivals, ''::text))::numeric)) / NULLIF(sum((NULLIF(scheduled_days, ''::text))::numeric), (0)::numeric)) AS late_arrival_rate_pct
   FROM fact_attendance_monthly
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m15_lop_days AS 
 SELECT period_end_date,
    department_id,
    sum((NULLIF(lop_days, ''::text))::numeric) AS lop_days
   FROM fact_payroll
  GROUP BY period_end_date, department_id
 HAVING (count(DISTINCT employee_id) >= 5);

CREATE OR REPLACE VIEW public.metric_m16_revenue AS 
 SELECT posting_period,
    sum((NULLIF(signed_amount_debit_positive, ''::text))::numeric) AS revenue
   FROM fact_ledger
  WHERE (account_code = ANY (ARRAY['4001'::text, '4002'::text, '4003'::text, '4004'::text]))
  GROUP BY posting_period;

CREATE OR REPLACE VIEW public.metric_m17_net_profit AS 
 SELECT posting_period,
    sum((NULLIF(signed_amount_debit_positive, ''::text))::numeric) AS net_profit
   FROM fact_ledger
  WHERE ((account_code ~ '^[0-9]+$'::text) AND (((account_code)::integer >= 4001) AND ((account_code)::integer <= 5999)))
  GROUP BY posting_period;

CREATE OR REPLACE VIEW public.metric_m18_operating_margin AS 
 WITH monthly AS (
         SELECT fact_ledger.posting_period,
            sum(
                CASE
                    WHEN (fact_ledger.account_code = ANY (ARRAY['4001'::text, '4002'::text, '4003'::text, '4004'::text])) THEN (NULLIF(fact_ledger.signed_amount_debit_positive, ''::text))::numeric
                    ELSE (0)::numeric
                END) AS revenue,
            sum(
                CASE
                    WHEN ((fact_ledger.account_code ~ '^[0-9]+$'::text) AND (((fact_ledger.account_code)::integer >= 4001) AND ((fact_ledger.account_code)::integer <= 5999))) THEN (NULLIF(fact_ledger.signed_amount_debit_positive, ''::text))::numeric
                    ELSE (0)::numeric
                END) AS net_profit
           FROM fact_ledger
          GROUP BY fact_ledger.posting_period
        )
 SELECT posting_period,
    revenue,
    net_profit,
    ((100.0 * net_profit) / NULLIF(revenue, (0)::numeric)) AS operating_margin_pct
   FROM monthly;

CREATE OR REPLACE VIEW public.metric_m19_payroll_pct_revenue AS 
 WITH payroll AS (
         SELECT (fact_payroll.period_end_date)::date AS metric_date,
            sum((NULLIF(fact_payroll.employer_cost, ''::text))::numeric) AS payroll_cost
           FROM fact_payroll
          GROUP BY (fact_payroll.period_end_date)::date
        ), revenue AS (
         SELECT fact_ledger.posting_period,
            sum((NULLIF(fact_ledger.signed_amount_debit_positive, ''::text))::numeric) AS revenue
           FROM fact_ledger
          WHERE (fact_ledger.account_code = ANY (ARRAY['4001'::text, '4002'::text, '4003'::text, '4004'::text]))
          GROUP BY fact_ledger.posting_period
        )
 SELECT p.metric_date,
    p.payroll_cost,
    r.revenue,
    ((100.0 * p.payroll_cost) / NULLIF(r.revenue, (0)::numeric)) AS payroll_pct_revenue
   FROM (payroll p
     JOIN revenue r ON ((to_char((p.metric_date)::timestamp with time zone, 'YYYY-MM'::text) = "left"(r.posting_period, 7))));

CREATE OR REPLACE VIEW public.metric_m20_dso AS 
 SELECT invoice_date,
    sum((NULLIF(balance_due, ''::text))::numeric) AS closing_receivables,
    (sum((NULLIF(total_amount, ''::text))::numeric) - sum((NULLIF(gst_amount, ''::text))::numeric)) AS revenue_ex_gst,
    ((90.0 * sum((NULLIF(balance_due, ''::text))::numeric)) / NULLIF((sum((NULLIF(total_amount, ''::text))::numeric) - sum((NULLIF(gst_amount, ''::text))::numeric)), (0)::numeric)) AS dso_days
   FROM fact_invoice
  WHERE (status <> ALL (ARRAY['DRAFT'::text, 'CANCELLED'::text]))
  GROUP BY invoice_date;

CREATE OR REPLACE VIEW public.metric_m21_overdue_receivables AS 
 SELECT invoice_date,
    sum((NULLIF(balance_due, ''::text))::numeric) AS overdue_receivables
   FROM fact_invoice
  WHERE ((due_date < invoice_date) AND (status <> ALL (ARRAY['DRAFT'::text, 'CANCELLED'::text])))
  GROUP BY invoice_date;

CREATE OR REPLACE VIEW public.metric_m22_task_completion_rate AS 
 SELECT team_id,
    count(*) FILTER (WHERE (status = 'Done'::text)) AS completed_tasks,
    count(*) AS total_tasks,
    ((100.0 * (count(*) FILTER (WHERE (status = 'Done'::text)))::numeric) / (NULLIF(count(*), 0))::numeric) AS completion_rate_pct
   FROM fact_task
  GROUP BY team_id;

CREATE OR REPLACE VIEW public.metric_m23_on_time_delivery_rate AS 
 SELECT team_id,
    sprint_id,
    count(*) FILTER (WHERE ((status = 'Done'::text) AND (completed_date IS NOT NULL) AND (due_date IS NOT NULL) AND (completed_date <= due_date))) AS on_time_tasks,
    count(*) FILTER (WHERE (status = 'Done'::text)) AS completed_tasks,
    ((100.0 * (count(*) FILTER (WHERE ((status = 'Done'::text) AND (completed_date IS NOT NULL) AND (due_date IS NOT NULL) AND (completed_date <= due_date))))::numeric) / (NULLIF(count(*) FILTER (WHERE (status = 'Done'::text)), 0))::numeric) AS on_time_delivery_rate_pct
   FROM fact_task
  GROUP BY team_id, sprint_id
 HAVING (count(*) FILTER (WHERE (status = 'Done'::text)) >= 5);

CREATE OR REPLACE VIEW public.metric_m24_velocity AS 
 SELECT team_id,
    sprint_id,
    sum((NULLIF(story_points, ''::text))::numeric) FILTER (WHERE (status = 'Done'::text)) AS completed_story_points
   FROM fact_task
  GROUP BY team_id, sprint_id
 HAVING (count(*) FILTER (WHERE (status = 'Done'::text)) >= 5);

CREATE OR REPLACE VIEW public.metric_m25_avg_cycle_time AS 
 SELECT team_id,
    sprint_id,
    round(avg((((NULLIF(completed_date, ''::text))::timestamp without time zone)::date - ((NULLIF(started_date, ''::text))::timestamp without time zone)::date)), 2) AS avg_cycle_time_days,
    count(*) AS completed_task_count
   FROM fact_task
  WHERE ((status = 'Done'::text) AND (NULLIF(started_date, ''::text) IS NOT NULL) AND (NULLIF(completed_date, ''::text) IS NOT NULL))
  GROUP BY team_id, sprint_id
 HAVING (count(*) >= 5);

CREATE OR REPLACE VIEW public.metric_m26_anomaly_flag_rate AS 
 SELECT source_dataset,
    (date_trunc('month'::text, (NULLIF(period, ''::text))::timestamp without time zone))::date AS month,
    round(((100.0 * (count(*) FILTER (WHERE (flagged = 'Y'::text)))::numeric) / (NULLIF(count(*), 0))::numeric), 2) AS anomaly_flag_rate_pct,
    count(*) AS record_count
   FROM fact_anomaly
  WHERE (NULLIF(period, ''::text) IS NOT NULL)
  GROUP BY source_dataset, ((date_trunc('month'::text, (NULLIF(period, ''::text))::timestamp without time zone))::date)
 HAVING (count(*) >= 5);

CREATE OR REPLACE VIEW public.metric_m27_high_risk_share AS 
 SELECT department_id,
    count(*) FILTER (WHERE (risk_band = 'High'::text)) AS high_risk_count,
    count(*) AS total_risk_records,
    round(((100.0 * (count(*) FILTER (WHERE (risk_band = 'High'::text)))::numeric) / (NULLIF(count(*), 0))::numeric), 2) AS high_risk_share_pct
   FROM fact_attrition_risk
  GROUP BY department_id
 HAVING (count(*) >= 10);

CREATE OR REPLACE VIEW public.metric_m28_forecast_error AS 
 SELECT f.forecast_month,
    f.department_id,
    f.metric,
    (NULLIF(f.forecast_value, ''::text))::numeric AS forecast_value,
    (h.headcount_end)::numeric AS actual_headcount,
        CASE
            WHEN ((h.headcount_end IS NULL) OR ((h.headcount_end)::numeric = (0)::numeric)) THEN NULL::numeric
            ELSE round(((abs(((h.headcount_end)::numeric - (NULLIF(f.forecast_value, ''::text))::numeric)) / (h.headcount_end)::numeric) * (100)::numeric), 2)
        END AS mape_pct,
        CASE
            WHEN (h.headcount_end IS NULL) THEN 'ACTUAL_NOT_AVAILABLE'::text
            WHEN ((h.headcount_end)::numeric = (0)::numeric) THEN 'ACTUAL_ZERO_MAPE_UNDEFINED'::text
            ELSE 'CALCULATED'::text
        END AS calculation_status
   FROM (fact_forecast f
     LEFT JOIN fact_headcount_monthly h ON (((date_trunc('month'::text, (f.forecast_month)::timestamp without time zone) = date_trunc('month'::text, (h.month_start_date)::timestamp without time zone)) AND (f.department_id = h.department_id))))
  WHERE (f.metric = 'headcount_end'::text);

