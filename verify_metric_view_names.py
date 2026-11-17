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
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name ~ '^metric_m[0-9]+_'
            ORDER BY table_name
        """)
        print("\n".join(r[0] for r in cur.fetchall()))
finally:
    conn.close()
