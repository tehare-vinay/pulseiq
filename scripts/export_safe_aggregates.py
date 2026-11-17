from pathlib import Path
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "Task 5 - First Dashboard" / ".env")

OUT = ROOT / "cloud_data_public"
OUT.mkdir(exist_ok=True)
MIN_GROUP_SIZE = 5

conn = psycopg2.connect(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
    user=os.getenv("PGUSER", "pulseiq_user"),
    password=os.getenv("PGPASSWORD", ""),
)

def read_table(name):
    return pd.read_sql_query(f'SELECT * FROM public."{name}"', conn)

def numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

try:
    # 1. Payroll: month and department aggregates
    df = read_table("fact_payroll")
    df = numeric(df, [
        "gross_pay", "net_pay", "employer_cost", "overtime_hours_paid"
    ])
    g = df.groupby(["period_end_date", "department_id"], dropna=False)
    payroll = g.agg(
        employee_count=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum"),
        overtime_hours=("overtime_hours_paid", "sum"),
    ).reset_index()
    payroll = payroll[payroll.employee_count >= MIN_GROUP_SIZE]
    payroll.drop(columns=["employee_count"]).to_csv(
        OUT / "cloud_payroll_monthly_department.csv", index=False
    )

    # 2. Headcount: month and department aggregates
    df = read_table("fact_headcount_monthly")
    df = numeric(df, [
        "headcount_start", "hires", "exits", "voluntary_exits",
        "transfers_in", "transfers_out", "headcount_end",
        "attrition_rate_monthly_pct"
    ])
    headcount = df.groupby(
        ["month_start_date", "department_id"], dropna=False
    ).agg(
        headcount_start=("headcount_start", "sum"),
        hires=("hires", "sum"),
        exits=("exits", "sum"),
        voluntary_exits=("voluntary_exits", "sum"),
        transfers_in=("transfers_in", "sum"),
        transfers_out=("transfers_out", "sum"),
        headcount_end=("headcount_end", "sum"),
    ).reset_index()
    headcount = headcount[headcount.headcount_end >= MIN_GROUP_SIZE]
    headcount.to_csv(OUT / "cloud_headcount_monthly_department.csv", index=False)

    # 3. Tasks: team and sprint aggregates
    df = read_table("fact_task")
    df = numeric(df, ["story_points", "cycle_time_days", "reopened_count"])
    df["_status"] = df["status"].astype(str).str.lower().str.strip()
    df["_on_time"] = df["completed_on_time"].astype(str).str.lower().isin(
        ["true", "t", "1", "yes"]
    )
    df["_overdue"] = df["is_overdue_at_cutoff"].astype(str).str.lower().isin(
        ["true", "t", "1", "yes"]
    )
    g = df.groupby(["team_id", "sprint_id"], dropna=False)
    tasks = g.agg(
        assignee_count=("assignee_employee_id", "nunique"),
        task_count=("task_id", "count"),
        completed_tasks=("_status", lambda s: s.eq("completed").sum()),
        cancelled_tasks=("_status", lambda s: s.eq("cancelled").sum()),
        overdue_tasks=("_overdue", "sum"),
        on_time_completed_tasks=("_on_time", "sum"),
        story_points=("story_points", "sum"),
        average_cycle_time_days=("cycle_time_days", "mean"),
        reopen_events=("reopened_count", "sum"),
    ).reset_index()
    tasks = tasks[tasks.assignee_count >= MIN_GROUP_SIZE]
    tasks.drop(columns=["assignee_count"]).to_csv(
        OUT / "cloud_team_sprint_productivity.csv", index=False
    )

    # 4. Anomalies: source dataset and period aggregates
    df = read_table("fact_anomaly")
    df["money_at_risk"] = pd.to_numeric(
        df["money_at_risk"], errors="coerce"
    ).fillna(0)
    df["_flagged"] = df["flagged"].astype(str).str.lower().isin(
        ["true", "t", "1", "yes"]
    )
    g = df.groupby(["source_dataset", "period"], dropna=False)
    anomalies = g.agg(
        employee_count=("employee_id", "nunique"),
        anomaly_records=("result_id", "count"),
        flagged_records=("_flagged", "sum"),
        money_at_risk=("money_at_risk", "sum"),
    ).reset_index()
    anomalies = anomalies[anomalies.employee_count >= MIN_GROUP_SIZE]
    anomalies.drop(columns=["employee_count"]).to_csv(
        OUT / "cloud_anomaly_summary.csv", index=False
    )

    # 5. Forecasts: month, department and metric aggregates
    df = read_table("fact_forecast")
    df = numeric(df, ["forecast_value", "lower_80", "upper_80"])
    forecasts = df.groupby(
        ["forecast_month", "department_id", "metric"], dropna=False
    ).agg(
        forecast_value=("forecast_value", "mean"),
        lower_80=("lower_80", "mean"),
        upper_80=("upper_80", "mean"),
    ).reset_index()
    forecasts.to_csv(OUT / "cloud_forecast_summary.csv", index=False)

    print("\nAggregate exports completed:")
    for file in sorted(OUT.glob("cloud_*.csv")):
        print(f"{file.name}: {len(pd.read_csv(file))} rows")
    size = sum(f.stat().st_size for f in OUT.glob("*.csv"))
    print(f"\nAll public CSV size: {size / (1024 * 1024):.3f} MB")
    print("Minimum group-size rule:", MIN_GROUP_SIZE)

finally:
    conn.close()
