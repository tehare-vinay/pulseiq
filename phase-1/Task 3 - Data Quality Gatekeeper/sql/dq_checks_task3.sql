-- PulseIQ Analytics / Task 3 - Data Quality Gatekeeper
-- SQL rule pack: DQ-C01 to DQ-C14
-- Run against pulseiq_warehouse. Review comments for checks requiring source-specific mapping.
\pset pager off

-- DQ-C01 Payroll equals ledger; expected to expose current differences (tolerance 0.01).
WITH p AS (
 SELECT TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') AS month_key,
        SUM(NULLIF(REGEXP_REPLACE(employer_cost,'[^0-9.-]','','g'),'')::numeric) payroll_cost
 FROM public.fact_payroll GROUP BY 1
), l AS (
 SELECT posting_period month,
        SUM(NULLIF(debit,'')::numeric)-SUM(NULLIF(credit,'')::numeric) ledger_cost
 FROM public.fact_ledger WHERE account_code IN ('5001','5002','5003','5004','5005') GROUP BY 1
)
SELECT 'DQ-C01' check_id,p."month",ROUND(p.payroll_cost,2) payroll_cost,ROUND(l.ledger_cost,2) ledger_cost,
       ROUND(p.payroll_cost-l.ledger_cost,2) difference,
       CASE WHEN ABS(p.payroll_cost-l.ledger_cost)<=0.01 THEN 'PASS' ELSE 'FAIL' END status
FROM p JOIN l USING(month) ORDER BY p."month";

-- DQ-C02 Ledger balanced by journal entry; returns only failures.
SELECT 'DQ-C02' check_id,entry_id,
       SUM(COALESCE(NULLIF(debit,'')::numeric,0)) total_debit,
       SUM(COALESCE(NULLIF(credit,'')::numeric,0)) total_credit,
       SUM(COALESCE(NULLIF(debit,'')::numeric,0))-SUM(COALESCE(NULLIF(credit,'')::numeric,0)) difference
FROM public.fact_ledger GROUP BY entry_id
HAVING ABS(SUM(COALESCE(NULLIF(debit,'')::numeric,0))-SUM(COALESCE(NULLIF(credit,'')::numeric,0)))>0.005
ORDER BY entry_id;

-- DQ-C03 Duplicate payroll rows: one employee per payroll run.
SELECT 'DQ-C03' check_id,employee_id,run_id,COUNT(*) row_count
FROM public.fact_payroll GROUP BY employee_id,run_id HAVING COUNT(*)>1
ORDER BY run_id,employee_id;

-- DQ-C04a Employee ID referential integrity.
SELECT 'DQ-C04a' check_id,f.payroll_item_id,f.employee_id,f.employee_key
FROM public.fact_payroll f LEFT JOIN public.dim_employee d ON d.employee_id=f.employee_id
WHERE d.employee_id IS NULL ORDER BY f.employee_id;

-- DQ-C04b SCD employee-key referential integrity.
SELECT 'DQ-C04b' check_id,f.payroll_item_id,f.employee_id,f.employee_key
FROM public.fact_payroll f LEFT JOIN public.dim_employee d ON d.employee_key=f.employee_key
WHERE f.employee_key IS NOT NULL AND d.employee_key IS NULL ORDER BY f.employee_id;

-- DQ-C05 Attendance after employee exit month; match the historical employee version.
SELECT 'DQ-C05' check_id,a.attendance_fact_id,a.employee_id,a.employee_key,a.period_end_date,d.exit_date
FROM public.fact_attendance_monthly a
JOIN public.dim_employee d ON d.employee_key=a.employee_key
WHERE NULLIF(d.exit_date,'') IS NOT NULL
  AND LEFT(a.period_end_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND LEFT(d.exit_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND TO_DATE(LEFT(a.period_end_date,10),'YYYY-MM-DD') >
      (DATE_TRUNC('month',TO_DATE(LEFT(d.exit_date,10),'YYYY-MM-DD'))+INTERVAL '1 month - 1 day')::date
ORDER BY a.employee_id,a.period_end_date;

-- DQ-C06 Compare monthly unpaid attendance days to payroll LOP days; review business mapping if partial days differ.
WITH a AS (
 SELECT employee_id,TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') month_key,
        SUM(COALESCE(NULLIF(REGEXP_REPLACE(unpaid_absence_days,'[^0-9.-]','','g'), '')::numeric,0)
           +COALESCE(NULLIF(REGEXP_REPLACE(half_days_unpaid,'[^0-9.-]','','g'), '')::numeric,0)) attendance_unpaid_days
 FROM public.fact_attendance_monthly GROUP BY employee_id,2
), p AS (
 SELECT employee_id,TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') month_key,
        SUM(COALESCE(NULLIF(REGEXP_REPLACE(lop_days,'[^0-9.-]','','g'), '')::numeric,0)) payroll_lop_days
 FROM public.fact_payroll GROUP BY employee_id,2
)
SELECT 'DQ-C06' check_id,COALESCE(a.employee_id,p.employee_id) employee_id,COALESCE(a."month_key",p."month_key") month_key,
       COALESCE(a.attendance_unpaid_days,0) attendance_unpaid_days,COALESCE(p.payroll_lop_days,0) payroll_lop_days
FROM a FULL JOIN p USING(employee_id,month_key)
WHERE ABS(COALESCE(a.attendance_unpaid_days,0)-COALESCE(p.payroll_lop_days,0))>0.01
ORDER BY month_key,employee_id;

-- DQ-C07 Invoice paid amount must not exceed total; balance must not be negative.
SELECT 'DQ-C07' check_id,invoice_id,total_amount,amount_paid,balance_due
FROM public.fact_invoice
WHERE COALESCE(NULLIF(REGEXP_REPLACE(amount_paid,'[^0-9.-]','','g'), '')::numeric,0)>
      COALESCE(NULLIF(REGEXP_REPLACE(total_amount,'[^0-9.-]','','g'), '')::numeric,0)+0.01
   OR COALESCE(NULLIF(REGEXP_REPLACE(balance_due,'[^0-9.-]','','g'), '')::numeric,0)<-0.01
ORDER BY invoice_id;

-- DQ-C08 Expense total = amount excluding GST + GST.
SELECT 'DQ-C08' check_id,expense_id,amount_excl_gst,gst_amount,total_amount,
       COALESCE(NULLIF(REGEXP_REPLACE(total_amount,'[^0-9.-]','','g'), '')::numeric,0)
      -COALESCE(NULLIF(REGEXP_REPLACE(amount_excl_gst,'[^0-9.-]','','g'), '')::numeric,0)
      -COALESCE(NULLIF(REGEXP_REPLACE(gst_amount,'[^0-9.-]','','g'), '')::numeric,0) difference
FROM public.fact_expense
WHERE ABS(COALESCE(NULLIF(REGEXP_REPLACE(total_amount,'[^0-9.-]','','g'), '')::numeric,0)
         -COALESCE(NULLIF(REGEXP_REPLACE(amount_excl_gst,'[^0-9.-]','','g'), '')::numeric,0)
         -COALESCE(NULLIF(REGEXP_REPLACE(gst_amount,'[^0-9.-]','','g'), '')::numeric,0))>0.01
ORDER BY expense_id;

-- DQ-C09 Completed date cannot precede started date; Done requires completed_date.
SELECT 'DQ-C09' check_id,task_id,status,started_date,completed_date
FROM public.fact_task
WHERE (NULLIF(started_date,'') IS NOT NULL AND NULLIF(completed_date,'') IS NOT NULL
       AND LEFT(started_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       AND LEFT(completed_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       AND TO_DATE(LEFT(completed_date,10),'YYYY-MM-DD')<TO_DATE(LEFT(started_date,10),'YYYY-MM-DD'))
   OR (status='Done' AND NULLIF(completed_date,'') IS NULL)
ORDER BY task_id;

-- DQ-C10 Leave end date must not precede leave start date.
SELECT 'DQ-C10' check_id,leave_request_id,employee_id,start_date,end_date
FROM public.fact_leave
WHERE NULLIF(start_date,'') IS NOT NULL AND NULLIF(end_date,'') IS NOT NULL
  AND LEFT(start_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND LEFT(end_date,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND TO_DATE(LEFT(end_date,10),'YYYY-MM-DD')<TO_DATE(LEFT(start_date,10),'YYYY-MM-DD')
ORDER BY leave_request_id;

-- DQ-C11 AI freshness: schema-specific template.
-- First discover actual AI table/columns:
-- SELECT table_name,column_name,data_type FROM information_schema.columns
-- WHERE table_schema='public' AND (table_name ILIKE '%ai%' OR table_name ILIKE '%prediction%')
--    AND (column_name ILIKE '%as_of%' OR column_name ILIKE '%score%' OR column_name ILIKE '%batch%');
-- Then implement: as_of_date within 7 days of batch_date AND scored_at between as_of_date and as_of_date + 24 hours.
-- Do not run a guessed table name.

-- DQ-C12 SCD2 validity ranges overlap for the same employee.
-- TEXT dates are guarded before conversion. Inclusive end dates are used per current catalog example.
SELECT 'DQ-C12' check_id,a.employee_id,a.employee_key employee_key_a,b.employee_key employee_key_b,
       a.valid_from valid_from_a,a.valid_to valid_to_a,b.valid_from valid_from_b,b.valid_to valid_to_b
FROM public.dim_employee a
JOIN public.dim_employee b ON a.employee_id=b.employee_id AND a.employee_key<b.employee_key
WHERE LEFT(a.valid_from,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND LEFT(b.valid_from,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  AND (NULLIF(a.valid_to,'') IS NULL OR LEFT(a.valid_to,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  AND (NULLIF(b.valid_to,'') IS NULL OR LEFT(b.valid_to,10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  AND TO_DATE(LEFT(a.valid_from,10),'YYYY-MM-DD') <= COALESCE(TO_DATE(NULLIF(LEFT(b.valid_to,10),''),'YYYY-MM-DD'),'9999-12-31'::date)
  AND TO_DATE(LEFT(b.valid_from,10),'YYYY-MM-DD') <= COALESCE(TO_DATE(NULLIF(LEFT(a.valid_to,10),''),'YYYY-MM-DD'),'9999-12-31'::date)
ORDER BY a.employee_id,a.employee_key,b.employee_key;

-- DQ-C13 Pipeline freshness: use latest SUCCESSFUL run only.
-- Verify the log schema first:
-- SELECT column_name,data_type FROM information_schema.columns
-- WHERE table_schema='public' AND table_name='etl_run_log';
-- If columns are status and finished_at, run:
-- SELECT 'DQ-C13' check_id,MAX(finished_at) latest_successful_finish,
--        CURRENT_TIMESTAMP-MAX(finished_at) age
-- FROM public.etl_run_log
-- WHERE UPPER(status) IN ('SUCCESS','SUCCEEDED','COMPLETED')
-- HAVING MAX(finished_at) IS NULL OR MAX(finished_at)<CURRENT_TIMESTAMP-INTERVAL '24 hours';

-- DQ-C14 Aggregate minimum group size: privacy rule for manager-facing aggregates.
-- Must be attached to the real manager-facing aggregate query, not a row-level table scan.
-- Template: SELECT <group columns>,COUNT(DISTINCT employee_id) employee_count
-- FROM <manager_aggregate_source> GROUP BY <group columns>
-- HAVING COUNT(DISTINCT employee_id)<5;

-- DQ-C11, C13, C14 remain documented templates until actual source/report schemas are confirmed.








