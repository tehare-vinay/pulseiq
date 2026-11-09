-- PulseIQ Task 2: row-count reconciliation against Task 1 passed clean rows.
-- First run the patched Task 1 ETL so fact_leave output_rows=3439 and rejected_rows=2.
-- Then run this script:
-- docker compose exec -T postgres psql -U pulseiq_user -d pulseiq_warehouse -v ON_ERROR_STOP=1 -f /app/sql/task2_row_count_reconciliation.sql
WITH expected(table_name, task1_input_rows, task1_rejected_rows, task1_passed_rows) AS (
    VALUES
      ('fact_payroll'::text, 7344::bigint, 0::bigint, 7344::bigint),
      ('fact_attendance_monthly', 7343::bigint, 0::bigint, 7343::bigint),
      ('fact_headcount_monthly', 891::bigint, 0::bigint, 891::bigint),
      ('fact_leave', 3441::bigint, 2::bigint, 3439::bigint)
), actual AS (
    SELECT 'fact_payroll'::text AS table_name, COUNT(*)::bigint AS warehouse_rows FROM warehouse.fact_payroll
    UNION ALL SELECT 'fact_attendance_monthly', COUNT(*)::bigint FROM warehouse.fact_attendance_monthly
    UNION ALL SELECT 'fact_headcount_monthly', COUNT(*)::bigint FROM warehouse.fact_headcount_monthly
    UNION ALL SELECT 'fact_leave', COUNT(*)::bigint FROM warehouse.fact_leave
)
SELECT e.table_name, e.task1_input_rows, e.task1_rejected_rows, e.task1_passed_rows,
       a.warehouse_rows, a.warehouse_rows - e.task1_passed_rows AS difference,
       CASE WHEN a.warehouse_rows = e.task1_passed_rows THEN 'PASS' ELSE 'FAIL' END AS reconciliation_status
FROM expected e JOIN actual a USING (table_name)
ORDER BY e.table_name;
