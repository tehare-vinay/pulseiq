from pathlib import Path
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "Task 5 - First Dashboard" / ".env")

views = [
    "vw_task11_expense_by_category",
    "vw_task11_monthly_expense_bills",
    "vw_task11_monthly_pnl",
    "vw_task11_top10_vendors",
    "vw_task12_client_days_to_pay",
    "vw_task12_monthly_cash_flow",
    "vw_task12_overdue_clients",
    "vw_task12_receivables_ageing",
]

conn = psycopg2.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", ""),
)

try:
    out = ROOT / "cloud_data"
    for view in views:
        query = sql.SQL("SELECT * FROM public.{}").format(
            sql.Identifier(view)
        )
        df = pd.read_sql_query(query.as_string(conn), conn)
        df.to_csv(out / f"{view}.csv", index=False)
        print(f"{view}: {len(df)} rows exported")
finally:
    conn.close()
