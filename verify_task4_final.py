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
            SELECT COUNT(*) FROM public.metric_catalog
        """)
        print("Catalog metrics:", cur.fetchone()[0])

        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name ~ '^metric_m[0-9]+_'
        """)
        print("Metric views:", cur.fetchone()[0])

        cur.execute("""
            SELECT metric_id, metric_name, minimum_group_size
            FROM public.metric_catalog
            ORDER BY metric_id
        """)
        for row in cur.fetchall():
            print(row)
finally:
    conn.close()
