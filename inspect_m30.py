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
            SELECT pg_get_viewdef('public.metric_m30_headcount_by_work_mode'::regclass, true)
        """)
        row = cur.fetchone()
        print(row[0] if row else "View definition not found")
finally:
    conn.close()
