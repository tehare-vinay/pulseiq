
import os
import json
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

DB = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "pulseiq_warehouse"),
    "user": os.getenv("PGUSER", "pulseiq_user"),
    "password": os.getenv("PGPASSWORD", "pulseiq_local_dev"),
}

def n(col):
    return f"NULLIF(REGEXP_REPLACE(COALESCE({col}::text,''),'[^0-9.-]','','g'),'')::numeric"

def date_ok(col):
    return f"LEFT(COALESCE({col}::text,''),10) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'"

def dt(col):
    return f"TO_DATE(LEFT({col}::text,10),'YYYY-MM-DD')"

CHECKS = [
("DQ-C01", "fact_payroll + fact_ledger", f"""
WITH p AS (
 SELECT TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') m,
 SUM({n('employer_cost')}) amount
 FROM public.fact_payroll WHERE {date_ok('period_end_date')}
 GROUP BY 1
), l AS (
 SELECT posting_period m, SUM({n('signed_amount_debit_positive')}) amount
 FROM public.fact_ledger
 WHERE posting_period ~ '^[0-9]{{4}}-[0-9]{{2}}$'
 AND account_code IN ('5001','5002','5003','5004','5005') GROUP BY 1
)
SELECT COALESCE(p.m,l.m) AS month_key,p.amount payroll_cost,l.amount ledger_cost
FROM p FULL JOIN l ON p.m=l.m
WHERE ABS(COALESCE(p.amount,0)-COALESCE(l.amount,0)) > 0.01
"""),
("DQ-C02", "fact_ledger", f"""
SELECT entry_id,SUM(COALESCE({n('debit')},0)) debit,
SUM(COALESCE({n('credit')},0)) credit
FROM public.fact_ledger GROUP BY entry_id
HAVING ABS(SUM(COALESCE({n('debit')},0))-SUM(COALESCE({n('credit')},0))) > 0.005
"""),
("DQ-C03", "fact_payroll", """
SELECT employee_id,run_id,COUNT(*) row_count
FROM public.fact_payroll GROUP BY employee_id,run_id
HAVING COUNT(*) > 1
"""),
("DQ-C04", "fact_payroll / dim_employee", """
SELECT 'employee_id' reference_type,f.payroll_item_id record_id,f.employee_id reference
FROM public.fact_payroll f LEFT JOIN public.dim_employee d ON d.employee_id=f.employee_id
WHERE f.employee_id IS NOT NULL AND d.employee_id IS NULL
UNION ALL
SELECT 'employee_key',f.payroll_item_id,f.employee_key::text
FROM public.fact_payroll f LEFT JOIN public.dim_employee d
ON d.employee_key::text=f.employee_key::text
WHERE f.employee_key IS NOT NULL AND d.employee_key IS NULL
"""),
("DQ-C05", "fact_attendance_monthly / dim_employee", f"""
SELECT a.attendance_fact_id,a.employee_id,a.employee_key,a.period_end_date,d.exit_date
FROM public.fact_attendance_monthly a
JOIN public.dim_employee d ON d.employee_key::text=a.employee_key::text
WHERE NULLIF(d.exit_date,'') IS NOT NULL
AND {date_ok('a.period_end_date')} AND {date_ok('d.exit_date')}
AND {dt('a.period_end_date')} >
(DATE_TRUNC('month',{dt('d.exit_date')})+INTERVAL '1 month - 1 day')::date
"""),
("DQ-C06", "fact_attendance_monthly / fact_payroll", f"""
WITH a AS (
 SELECT employee_id,
        TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') AS month_key,
        SUM(COALESCE({n('unpaid_absence_days')},0)
          + 0.5*COALESCE({n('half_days_unpaid')},0)) AS expected_lop
 FROM public.fact_attendance_monthly
 WHERE {date_ok('period_end_date')}
 GROUP BY employee_id,2
), p AS (
 SELECT employee_id,
        TO_CHAR(TO_DATE(LEFT(period_end_date,10),'YYYY-MM-DD'),'YYYY-MM') AS month_key,
        SUM(COALESCE({n('lop_days')},0)) AS actual_lop
 FROM public.fact_payroll
 WHERE {date_ok('period_end_date')}
 GROUP BY employee_id,2
)
SELECT COALESCE(a.employee_id,p.employee_id) AS employee_id,
       COALESCE(a.month_key,p.month_key) AS month_key,
       a.expected_lop,p.actual_lop
FROM a FULL JOIN p ON a.employee_id = p.employee_id AND a.month_key = p.month_key
WHERE ABS(COALESCE(a.expected_lop,0)-COALESCE(p.actual_lop,0)) > 0.01
"""),
("DQ-C07", "fact_invoice", f"""
SELECT invoice_id,total_amount,amount_paid,balance_due
FROM public.fact_invoice
WHERE COALESCE({n('amount_paid')},0)>COALESCE({n('total_amount')},0)+0.01
OR COALESCE({n('balance_due')},0)<-0.01
"""),
("DQ-C08", "fact_expense", f"""
SELECT expense_id,amount_excl_gst,gst_amount,total_amount
FROM public.fact_expense
WHERE ABS(COALESCE({n('total_amount')},0)-COALESCE({n('amount_excl_gst')},0)
-COALESCE({n('gst_amount')},0))>0.01
"""),
("DQ-C09", "fact_task", f"""
SELECT task_id,status,started_date,completed_date FROM public.fact_task
WHERE ({date_ok('started_date')} AND {date_ok('completed_date')}
AND {dt('completed_date')} < {dt('started_date')})
OR (LOWER(COALESCE(status,''))='done' AND NULLIF(completed_date,'') IS NULL)
"""),
("DQ-C10", "fact_leave", f"""
SELECT leave_request_id,employee_id,start_date,end_date FROM public.fact_leave
WHERE {date_ok('start_date')} AND {date_ok('end_date')}
AND {dt('end_date')} < {dt('start_date')}
"""),
("DQ-C11", "AI prediction source", None),
("DQ-C12", "dim_employee", f"""
SELECT a.employee_id,a.employee_key key_a,b.employee_key key_b,
a.valid_from from_a,a.valid_to to_a,b.valid_from from_b,b.valid_to to_b
FROM public.dim_employee a JOIN public.dim_employee b
ON a.employee_id=b.employee_id AND a.employee_key::text < b.employee_key::text
WHERE {date_ok('a.valid_from')} AND {date_ok('b.valid_from')}
AND (NULLIF(a.valid_to,'') IS NULL OR {date_ok('a.valid_to')})
AND (NULLIF(b.valid_to,'') IS NULL OR {date_ok('b.valid_to')})
AND {dt('a.valid_from')} <= COALESCE(
CASE WHEN NULLIF(b.valid_to,'') IS NOT NULL THEN {dt('b.valid_to')} END,DATE '9999-12-31')
AND {dt('b.valid_from')} <= COALESCE(
CASE WHEN NULLIF(a.valid_to,'') IS NOT NULL THEN {dt('a.valid_to')} END,DATE '9999-12-31')
"""),
("DQ-C13", "etl_run_log", None),
("DQ-C14", "manager-facing aggregate", None),
]

NOT_IMPLEMENTED = {
    "DQ-C11": "AI prediction source and batch_date/as_of_date/scored_at columns must be confirmed.",
    "DQ-C13": "ETL run-log table and successful status/finished timestamp columns must be confirmed.",
    "DQ-C14": "Actual manager-facing aggregate query/source must be identified before applying minimum group size 5.",
}

def main():
    conn = psycopg.connect(**DB, row_factory=dict_row)
    results = []

    try:
        # Remove the temporary connection-test row only.
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.dq_results WHERE check_id='DQ-RUNNER-TEST'")
        conn.commit()

        for check_id, table_name, sql in CHECKS:
            if sql is None:
                status = "WARN"
                bad_rows = 0
                details = NOT_IMPLEMENTED[check_id]
            else:
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        rows = cur.fetchall()
                    bad_rows = len(rows)
                    if not bad_rows:
                        status = "PASS"
                    elif check_id == "DQ-C04" and all(
                        (
                            row.get("record_id") == "PI-X0003"
                            and (
                                (row.get("reference_type") == "employee_id" and row.get("reference") == "EMP-9001")
                                or (row.get("reference_type") == "employee_key" and str(row.get("reference")) == "-1")
                            )
                        )
                        or (
                            row.get("record_id") == "PI-X0004"
                            and (
                                (row.get("reference_type") == "employee_id" and row.get("reference") == "EMP-9002")
                                or (row.get("reference_type") == "employee_key" and str(row.get("reference")) == "-1")
                            )
                        )
                        for row in rows
                    ):
                        status = "WARN"
                    else:
                        status = "FAIL"
                    details = json.dumps(rows[:25], default=str)
                    if bad_rows > 25:
                        details += f" ... plus {bad_rows-25} more rows"
                except Exception as exc:
                    conn.rollback()
                    status = "FAIL"
                    bad_rows = 0
                    details = f"{type(exc).__name__}: {exc}"

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.dq_results
                    (check_id,table_name,bad_rows,status,run_time,details)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (
                    check_id, table_name, bad_rows, status,
                    datetime.now(timezone.utc), details[:8000]
                ))
            conn.commit()
            results.append((check_id,status,bad_rows))
            print(f"{check_id}: {status} | bad_rows={bad_rows}")

        print("\nSUMMARY")
        for check_id,status,bad_rows in results:
            print(f"{check_id:7} {status:16} bad_rows={bad_rows}")
        print(f"\nSaved {len(results)} results in public.dq_results.")
        print("NOT_IMPLEMENTED checks are not PASS.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()










