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
        for name in [
            "metric_m02_hires_total",
            "metric_m03_exits_total",
            "metric_m29_headcount_by_work_location",
            "metric_m30_headcount_by_work_mode",
            "metric_m31_headcount_by_location_tier"
        ]:
            cur.execute(
                "SELECT pg_get_viewdef(%s::regclass, true)",
                ("public." + name,)
            )
            row = cur.fetchone()
            print(f"\n--- {name} ---\n{row[0] if row else 'Not found'}")
finally:
    conn.close()
