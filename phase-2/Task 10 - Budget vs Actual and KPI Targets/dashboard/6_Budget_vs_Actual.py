
import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="Budget vs Actual and KPI Targets",
    page_icon="📊",
    layout="wide",
)

st.title("Budget vs Actual and KPI Targets")
st.caption("Task 10 | KPI target traffic lights")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


@st.cache_data(ttl=300)
def read_query(query):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=300)
def load_kpi_data():
    return read_query("""
        WITH task_month AS (
            SELECT
                date_trunc('month', f.due_date::date)::date AS month,
                tm.department_id,
                COUNT(*) AS total_tasks,
                COUNT(*) FILTER (
                    WHERE f.status = 'Done'
                ) AS completed_tasks,
                100.0 * COUNT(*) FILTER (
                    WHERE f.status = 'Done'
                ) / NULLIF(COUNT(*), 0) AS completion_rate_pct
            FROM public.fact_task f
            JOIN public.dim_team tm
              ON tm.team_id = f.team_id
            WHERE NULLIF(TRIM(f.due_date), '') IS NOT NULL
            GROUP BY 1, 2
        )
        SELECT
            t.month::date AS month,
            t.department_id,

            t.attendance_rate_target::numeric * 100
                AS attendance_target,
            a.attendance_rate_pct AS attendance_actual,

            t.attrition_monthly_target_pct::numeric
                AS attrition_target,
            r.attrition_rate_pct AS attrition_actual,

            t.overtime_share_target_pct::numeric
                AS overtime_target,
            o.overtime_share_pct AS overtime_actual,

            t.task_completion_target_pct::numeric
                AS task_completion_target,
            tm.completion_rate_pct AS task_completion_actual,
            tm.total_tasks,
            tm.completed_tasks

        FROM public.kpi_targets t

        LEFT JOIN public.metric_m13_attendance_rate a
          ON date_trunc(
                'month', a.period_end_date::date
             )::date = t.month::date
         AND a.department_id = t.department_id

        LEFT JOIN public.metric_m11_overtime_share o
          ON date_trunc(
                'month', o.period_end_date::date
             )::date = t.month::date
         AND o.department_id = t.department_id

        LEFT JOIN public.metric_m04_attrition_rate r
          ON r.month_start_date::date = t.month::date
         AND r.department_id = t.department_id

        LEFT JOIN task_month tm
          ON tm.month = t.month::date
         AND tm.department_id = t.department_id

        ORDER BY t.month, t.department_id
    """)


@st.cache_data(ttl=300)
def load_metric_rules():
    return read_query("""
        SELECT
            metric_id,
            good_direction,
            minimum_group_size
        FROM public.metric_dictionary
        WHERE metric_id IN ('M13', 'M04', 'M11', 'M22')
    """)


def traffic_light(actual, target, direction, group_size, minimum):
    if pd.isna(actual) or pd.isna(target):
        return "🟠 Amber — Not assessable"

    if pd.isna(group_size) or group_size < minimum:
        return "🟠 Amber — Below minimum group size"

    if direction == "Lower is better":
        return "🟢 Green" if actual <= target else "🔴 Red"

    if direction == "Higher is better":
        return "🟢 Green" if actual >= target else "🔴 Red"

    return "🟠 Amber — Direction unavailable"

try:
    df = load_kpi_data()
    rules_df = load_metric_rules()

    if df.empty:
        st.warning("No KPI target records found.")
        st.stop()

    if rules_df["metric_id"].nunique() != 4:
        st.error("One or more KPI metric rules are missing.")
        st.stop()

    # Convert values such as "5 tasks" into numeric 5.
    rules_df["minimum_group_size"] = pd.to_numeric(
        rules_df["minimum_group_size"]
        .astype(str)
        .str.extract(r"(\d+)")[0],
        errors="coerce",
    )

    rules = rules_df.set_index("metric_id").to_dict("index")

    numeric_columns = [
        "attendance_actual", "attendance_target",
        "attrition_actual", "attrition_target",
        "overtime_actual", "overtime_target",
        "task_completion_actual", "task_completion_target",
        "total_tasks", "completed_tasks",
    ]

    numeric_columns = [
        "attendance_actual", "attendance_target",
        "attrition_actual", "attrition_target",
        "overtime_actual", "overtime_target",
        "task_completion_actual", "task_completion_target",
        "total_tasks", "completed_tasks",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    st.info(
        "Green = target achieved. Red = target missed. "
        "Amber = actual/target unavailable or minimum group size not met."
    )

    departments = ["All"] + sorted(
        df["department_id"].dropna().astype(str).unique().tolist()
    )

    selected_department = st.selectbox("Department", departments)

    months = sorted(df["month"].dropna().unique())

    if not months:
        st.warning("No valid target months available.")
        st.stop()

    selected_month = st.selectbox(
        "Month",
        months,
        format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"),
    )

    filtered = df[df["month"] == selected_month].copy()

    if selected_department != "All":
        filtered = filtered[
            filtered["department_id"].astype(str) == selected_department
        ]

    # Apply directions and minimum group sizes from metric_dictionary.
    filtered["Attendance status"] = filtered.apply(
        lambda x: traffic_light(
            x["attendance_actual"],
            x["attendance_target"],
            rules["M13"]["good_direction"],
            5 if pd.notna(x["attendance_actual"]) else None,
            rules["M13"]["minimum_group_size"],
        ), axis=1
    )

    filtered["Attrition status"] = filtered.apply(
        lambda x: traffic_light(
            x["attrition_actual"],
            x["attrition_target"],
            rules["M04"]["good_direction"],
            10 if pd.notna(x["attrition_actual"]) else None,
            rules["M04"]["minimum_group_size"],
        ), axis=1
    )

    filtered["Overtime status"] = filtered.apply(
        lambda x: traffic_light(
            x["overtime_actual"],
            x["overtime_target"],
            rules["M11"]["good_direction"],
            5 if pd.notna(x["overtime_actual"]) else None,
            rules["M11"]["minimum_group_size"],
        ), axis=1
    )

    filtered["Task Completion status"] = filtered.apply(
        lambda x: traffic_light(
            x["task_completion_actual"],
            x["task_completion_target"],
            rules["M22"]["good_direction"],
            x["total_tasks"],
            rules["M22"]["minimum_group_size"],
        ), axis=1
    )

    st.subheader("KPI Traffic Lights")

    display = filtered[[
        "month",
        "department_id",
        "attendance_actual",
        "attendance_target",
        "Attendance status",
        "attrition_actual",
        "attrition_target",
        "Attrition status",
        "overtime_actual",
        "overtime_target",
        "Overtime status",
        "task_completion_actual",
        "task_completion_target",
        "total_tasks",
        "completed_tasks",
        "Task Completion status",
    ]].copy()

    display.rename(columns={
        "month": "Month",
        "department_id": "Department",
        "attendance_actual": "Attendance Actual (%)",
        "attendance_target": "Attendance Target (%)",
        "attrition_actual": "Attrition Actual (%)",
        "attrition_target": "Attrition Target (%)",
        "overtime_actual": "Overtime Actual (%)",
        "overtime_target": "Overtime Target (%)",
        "task_completion_actual": "Task Completion Actual (%)",
        "task_completion_target": "Task Completion Target (%)",
        "total_tasks": "Total Tasks",
        "completed_tasks": "Completed Tasks",
    }, inplace=True)

    percentage_columns = [
        "Attendance Actual (%)",
        "Attendance Target (%)",
        "Attrition Actual (%)",
        "Attrition Target (%)",
        "Overtime Actual (%)",
        "Overtime Target (%)",
        "Task Completion Actual (%)",
        "Task Completion Target (%)",
    ]

    for col in percentage_columns:
        display[col] = display[col].round(2)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Traffic-light directions and minimum group sizes follow "
        "metric_dictionary. Task completion is calculated monthly "
        "using tasks due in the month and mapped through dim_team. "
        "Missing or suppressed values are Amber."
    )

    # STEP 4: Department ranking by overspend
    st.subheader("Department Ranking by Overspend")

    ranking = read_query("""
        WITH budget AS (
            SELECT
                month::date AS month,
                department_id,
                SUM(NULLIF(TRIM(budget_payroll_cost), '')::numeric) AS budget
            FROM public.budget_payroll_dept_month
            GROUP BY 1, 2
        ),
        actual AS (
            SELECT
                date_trunc('month', period_end_date::date)::date AS month,
                department_id,
                SUM(employer_cost) AS actual
            FROM public.metric_m09_payroll_cost
            GROUP BY 1, 2
        ),
        monthly AS (
            SELECT
                b.month,
                b.department_id,
                b.budget,
                a.actual
            FROM budget b
            INNER JOIN actual a
                ON a.month = b.month
               AND a.department_id = b.department_id
        ),
        totals AS (
            SELECT
                department_id,
                SUM(budget) AS total_budget,
                SUM(actual) AS total_actual,
                SUM(actual - budget) AS variance,
                ROUND(
                    100 * SUM(actual - budget)
                    / NULLIF(SUM(budget), 0), 2
                ) AS variance_pct,
                COUNT(*) AS comparable_months
            FROM monthly
            GROUP BY department_id
        )
        SELECT
            DENSE_RANK() OVER (ORDER BY variance DESC) AS rank,
            department_id,
            ROUND(total_budget, 2) AS total_budget,
            ROUND(total_actual, 2) AS total_actual,
            ROUND(variance, 2) AS variance,
            variance_pct,
            comparable_months
        FROM totals
        ORDER BY rank
    """)

    st.caption(
        "Positive variance indicates overspend. "
        "Negative variance indicates underspend. "
        "Ranking uses months where both budget and governed actual "
        "payroll cost are available."
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )
    
except Exception as exc:
    st.error(f"Unable to load KPI traffic lights: {exc}")
