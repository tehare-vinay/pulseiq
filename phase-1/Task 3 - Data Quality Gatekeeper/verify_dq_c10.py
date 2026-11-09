import os
import psycopg

conn = psycopg.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=os.getenv("PGPORT", "5432"),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", "pulseiq_local_dev")
)
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT leave_request_id, start_date, end_date,
                   CASE
                     WHEN NULLIF(TRIM(start_date), '') IS NULL
                       OR NULLIF(TRIM(end_date), '') IS NULL
                     THEN 'MISSING_DATE'
                     WHEN TRIM(end_date)::date < TRIM(start_date)::date
                     THEN 'FAIL'
                     ELSE 'PASS'
                   END AS check_result
            FROM public.fact_leave
            WHERE leave_request_id IN ('LR-002286', 'LR-000025')
            ORDER BY leave_request_id
        """)
        for row in cur.fetchall():
            print(row)
finally:
    conn.close()
