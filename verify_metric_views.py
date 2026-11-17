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
              AND table_name LIKE 'metric_m%'
            ORDER BY table_name
        """)
        views = [r[0] for r in cur.fetchall()]
        print("Metric views found:", len(views))
        for v in views:
            cur.execute('SELECT COUNT(*) FROM public."' + v + '"')
            print(v, "rows:", cur.fetchone()[0])
finally:
    conn.close()
