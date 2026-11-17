import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "Task 5 - First Dashboard" / ".env", override=True)

OUT = ROOT / "cloud_data_parquet"
OUT.mkdir(exist_ok=True)

conn = psycopg2.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", ""),
    connect_timeout=10,
)

queries = {
    "task7_tenure_by_department": """
        SELECT
            department_id,
            COUNT(*) AS exit_records,
            ROUND(AVG(NULLIF(TRIM(tenure_days), '')::numeric), 1)
                AS avg_tenure_days
        FROM public.dim_employee
        WHERE NULLIF(TRIM(exit_date), '') IS NOT NULL
          AND NULLIF(TRIM(tenure_days), '') ~ '^[0-9]+([.][0-9]+)?$'
        GROUP BY department_id
        HAVING COUNT(*) >= 10
        ORDER BY department_id
    """,
    "task7_risk_by_department": """
        SELECT
            department_id,
            risk_band,
            COUNT(*) AS prediction_records
        FROM public.fact_attrition_risk
        WHERE NULLIF(TRIM(department_id), '') IS NOT NULL
          AND NULLIF(TRIM(risk_band), '') IS NOT NULL
        GROUP BY department_id, risk_band
        HAVING COUNT(*) >= 10
        ORDER BY department_id, risk_band
    """
}

try:
    for name, query in queries.items():
        df = pd.read_sql_query(query, conn)
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False, engine="pyarrow")

        check = pd.read_parquet(path)
        if len(check) != len(df) or list(check.columns) != list(df.columns):
            raise RuntimeError(f"Verification failed: {name}")

        print(f"Verified: {path.name} | Rows: {len(check)}")
finally:
    conn.close()

print("Task 7 aggregate export completed.")
