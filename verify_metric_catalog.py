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
            SELECT to_regclass('public.metric_dictionary'),
                   to_regclass('public.metric_catalog')
        """)
        print("Tables/views:", cur.fetchone())
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('metric_dictionary','metric_catalog')
            ORDER BY table_name
        """)
        print("Found:", cur.fetchall())
        if cur.execute("SELECT to_regclass('public.metric_dictionary')") is None:
            pass
        cur.execute("""
            SELECT COUNT(*) FROM public.metric_dictionary
        """)
        print("Dictionary rows:", cur.fetchone()[0])
        cur.execute("""
            SELECT COUNT(*) FROM public.metric_catalog
        """)
        print("Catalog rows:", cur.fetchone()[0])
finally:
    conn.close()
