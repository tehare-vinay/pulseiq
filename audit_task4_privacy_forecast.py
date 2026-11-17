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
        print("=== PRIVACY VIEW CHECKS ===")
        for view in [
            "metric_m02_hires_total",
            "metric_m03_exits_total",
            "metric_m29_headcount_by_work_location",
            "metric_m30_headcount_by_work_mode",
            "metric_m31_headcount_by_location_tier"
        ]:
            cur.execute(f'SELECT COUNT(*) FROM public."{view}"')
            print(f"{view}: {cur.fetchone()[0]} visible groups")

        print("\n=== FORECAST ERROR CHECK ===")
        cur.execute("""
            SELECT calculation_status, COUNT(*)
            FROM public.metric_m28_forecast_error
            GROUP BY calculation_status
            ORDER BY calculation_status
        """)
        rows = cur.fetchall()
        for status, count in rows:
            print(f"{status}: {count}")

        cur.execute("""
            SELECT forecast_month, department_id, forecast_value,
                   actual_headcount, mape_pct, calculation_status
            FROM public.metric_m28_forecast_error
            WHERE actual_headcount IS NULL
            LIMIT 5
        """)
        rows = cur.fetchall()
        print("\nRows with missing actuals:")
        for row in rows:
            print(row)
finally:
    conn.close()
