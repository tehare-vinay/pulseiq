import os
import psycopg
from psycopg.rows import dict_row

conn = psycopg.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=os.getenv("PGPORT", "5432"),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", "pulseiq_local_dev"),
    row_factory=dict_row
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT DISTINCT ON (check_id)
            check_id, status, bad_rows, run_time, details
        FROM public.dq_results
        WHERE check_id LIKE 'DQ-C%'
        ORDER BY check_id, run_time DESC
    """)
    for row in cur.fetchall():
        print(row)

conn.close()
