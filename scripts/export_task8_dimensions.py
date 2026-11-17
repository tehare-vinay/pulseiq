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
)

queries = {
    "dim_team": """
        SELECT team_id, team_name, active_members
        FROM public.dim_team
        ORDER BY team_name
    """,
    "dim_sprint": """
        SELECT sprint_id, sprint_name, working_days, start_date, end_date
        FROM public.dim_sprint
        ORDER BY start_date, sprint_id
    """
}

try:
    for name, query in queries.items():
        df = pd.read_sql_query(query, conn)
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False)
        check = pd.read_parquet(path)
        print(f"Verified: {path.name} | Rows: {len(check)}")
finally:
    conn.close()

print("Task 8 dimension export completed.")
