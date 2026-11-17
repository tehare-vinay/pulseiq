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
        print("=== FORECAST STATUS SUMMARY ===")
        cur.execute("""
            SELECT calculation_status, COUNT(*)
            FROM public.metric_m28_forecast_error
            GROUP BY calculation_status
            ORDER BY calculation_status
        """)
        for row in cur.fetchall():
            print(row)

        print("\n=== PRIVACY THRESHOLD CHECK ===")
        for view, column in [
            ("metric_m29_headcount_by_work_location", "headcount"),
            ("metric_m30_headcount_by_work_mode", "headcount"),
            ("metric_m31_headcount_by_location_tier", "headcount")
        ]:
            cur.execute(f"""
                SELECT MIN({column}), MAX({column}), COUNT(*),
                       COUNT(*) FILTER (WHERE {column} < 5)
                FROM public."{view}"
            """)
            print(view, cur.fetchone())
finally:
    conn.close()
