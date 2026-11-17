import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "Task 5 - First Dashboard" / ".env")

conn = psycopg2.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", ""),
    connect_timeout=10,
)

output_dir = ROOT / "cloud_data"
output_dir.mkdir(exist_ok=True)

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name LIKE 'metric_%'
            ORDER BY table_name;
        """)
        views = [row[0] for row in cur.fetchall()]

    total_bytes = 0

    for view in views:
        query = sql.SQL("SELECT * FROM public.{}").format(
            sql.Identifier(view)
        )
        df = pd.read_sql_query(query.as_string(conn), conn)
        file_path = output_dir / f"{view}.csv"
        df.to_csv(file_path, index=False)

        size = file_path.stat().st_size
        total_bytes += size
        print(f"{view}: {len(df)} rows | {size / 1024:.2f} KB")

    print("\nExport completed.")
    print(f"Views exported: {len(views)}")
    print(f"Total export size: {total_bytes / (1024 * 1024):.2f} MB")
    print(f"Export folder: {output_dir}")

    if total_bytes > 200 * 1024 * 1024:
        print("WARNING: Export exceeds the 200 MB limit.")
finally:
    conn.close()
