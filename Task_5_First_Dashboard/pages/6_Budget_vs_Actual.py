from pathlib import Path
import pandas as pd
import streamlit as st
from cloud_data import load_parquet

st.set_page_config(page_title="Budget vs Actual and KPI Targets", page_icon="📊", layout="wide")
st.title("Budget vs Actual and KPI Targets")
st.caption("Task 10 | KPI target traffic lights")


def first_column(df, candidates, required=True):
    for name in candidates:
        if name in df.columns:
            return name
    if required:
        raise KeyError(f"Required column not found. Tried: {candidates}; available: {list(df.columns)}")
    return None


def standardize_month(df, candidates):
    df = df.copy()
    col = first_column(df, candidates)
    df["month"] = pd.to_datetime(df[col], errors="coerce").dt.to_period("M").dt.to_timestamp()
    return df


def standardize_department(df):
    df = df.copy()
    col = first_column(df, ["department_id", "department", "dept_id"])
    df["department_id"] = df[col].astype("string")
    return df


def standardize_metric(df, metric_name, date_candidates, value_candidates):
    df = standardize_month(df, date_candidates)
    df = standardize_department(df)
    value_col = first_column(df, value_candidates)
    return df[["month", "department_id", value_col]].rename(columns={value_col: metric_name})


def traffic_light(actual, target, direction, group_size, minimum):
    if pd.isna(actual) or pd.isna(target):
        return "🟠 Amber — Not assessable"
    if pd.isna(group_size) or pd.isna(minimum) or group_size < minimum:
        return "🟠 Amber — Below minimum group size"
    if direction == "Lower is better":
        return "🟢 Green" if actual <= target else "🔴 Red"
    if direction == "Higher is better":
        return "🟢 Green" if actual >= target else "🔴 Red"
    return "🟠 Amber — Direction unavailable"


try:
    targets = load_parquet("metric_kpi_targets")
    attendance_raw = load_parquet("metric_m13_attendance_rate")
    attrition_raw = load_parquet("metric_m04_attrition_rate")
    overtime_raw = load_parquet("metric_m11_overtime_share")
    task_raw = load_parquet("metric_m22_task_completion_rate")
    catalog = load_parquet("metric_catalog")

    targets = standardize_month(targets, ["month", "month_start_date", "period_start_date", "period_end_date"])
    targets = standardize_department(targets)

    target_columns = {
        "attendance_target": ["attendance_rate_target", "attendance_target", "attendance_target_pct"],
        "attrition_target": ["attrition_monthly_target_pct", "attrition_target", "attrition_target_pct"],
        "overtime_target": ["overtime_share_target_pct", "overtime_target", "overtime_target_pct"],
        "task_completion_target": ["task_completion_target_pct", "task_completion_target", "task_completion_target_rate"],
    }
    for output, candidates in target_columns.items():
        col = first_column(targets, candidates)
        targets[output] = pd.to_numeric(targets[col], errors="coerce")
    # Attendance target is stored as a fraction in the warehouse; display as percent.
    if targets["attendance_target"].dropna().between(0, 1).all():
        targets["attendance_target"] *= 100

    attendance = standardize_metric(attendance_raw, "attendance_actual", ["period_end_date", "month_start_date", "month"], ["attendance_rate_pct", "attendance_rate", "actual"])
    attrition = standardize_metric(attrition_raw, "attrition_actual", ["month_start_date", "month", "period_end_date"], ["attrition_rate_pct", "attrition_rate", "actual"])
    overtime = standardize_metric(overtime_raw, "overtime_actual", ["period_end_date", "month_start_date", "month"], ["overtime_share_pct", "overtime_share", "actual"])
    # M22 is exported at team grain only (team_id, completed_tasks,
    # total_tasks, completion_rate_pct). It has no month or department columns,
    # so it must not be joined to department/month KPI targets.
    df = targets[["month", "department_id", *target_columns.keys()]].copy()
    for metric in [attendance, attrition, overtime]:
        df = df.merge(metric, on=["month", "department_id"], how="left")

    df["task_completion_actual"] = pd.NA
    df["total_tasks"] = pd.NA
    df["completed_tasks"] = pd.NA

    team_col = first_column(task_raw, ["team_id"])
    total_col = first_column(task_raw, ["total_tasks"])
    completed_col = first_column(task_raw, ["completed_tasks"])
    rate_col = first_column(task_raw, ["completion_rate_pct"])
    task_summary = task_raw[[team_col, completed_col, total_col, rate_col]].copy()
    task_summary[completed_col] = pd.to_numeric(task_summary[completed_col], errors="coerce")
    task_summary[total_col] = pd.to_numeric(task_summary[total_col], errors="coerce")
    task_summary[rate_col] = pd.to_numeric(task_summary[rate_col], errors="coerce")
    valid_tasks = task_summary.dropna(subset=[completed_col, total_col])
    valid_tasks = valid_tasks[valid_tasks[total_col] > 0]
    total_tasks_all = valid_tasks[total_col].sum()
    completed_tasks_all = valid_tasks[completed_col].sum()
    overall_task_completion = (
        100 * completed_tasks_all / total_tasks_all if total_tasks_all else float("nan")
    )
    task_team_display = task_summary.rename(columns={
        team_col: "Team",
        completed_col: "Completed Tasks",
        total_col: "Total Tasks",
        rate_col: "Completion Rate (%)",
    })
    task_team_display["Completion Rate (%)"] = task_team_display["Completion Rate (%)"].round(2)

    # Read metric direction and minimum group size from the exported metric catalog.
    id_col = first_column(catalog, ["metric_id", "metric_code", "metric_key"])
    direction_col = first_column(catalog, ["good_direction", "direction", "preferred_direction"], required=False)
    minimum_col = first_column(catalog, ["minimum_group_size", "min_group_size", "minimum_n"], required=False)
    catalog["_metric_id"] = catalog[id_col].astype(str).str.upper().str.replace("-", "", regex=False)
    defaults = {
        "M13": ("Higher is better", 5),
        "M04": ("Lower is better", 10),
        "M11": ("Lower is better", 5),
        "M22": ("Higher is better", 5),
    }
    rules = {}
    for key, default in defaults.items():
        row = catalog[catalog["_metric_id"].str.replace("M", "", regex=False).eq(key.replace("M", ""))]
        direction, minimum = default
        if not row.empty:
            if direction_col and pd.notna(row.iloc[0][direction_col]):
                direction = str(row.iloc[0][direction_col])
            if minimum_col and pd.notna(row.iloc[0][minimum_col]):
                minimum = pd.to_numeric(pd.Series([row.iloc[0][minimum_col]]), errors="coerce").iloc[0]
        rules[key] = (direction, minimum)

    if df.empty:
        st.warning("No KPI target records found.")
        st.stop()

    st.info("Green = target achieved. Red = target missed. Amber = actual/target unavailable or minimum group size not met.")
    departments = ["All"] + sorted(df["department_id"].dropna().astype(str).unique().tolist())
    selected_department = st.selectbox("Department", departments)
    months = sorted(df["month"].dropna().unique())
    if not months:
        st.warning("No valid target months available.")
        st.stop()
    selected_month = st.selectbox("Month", months, format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"))
    filtered = df[df["month"].eq(selected_month)].copy()
    if selected_department != "All":
        filtered = filtered[filtered["department_id"].astype(str).eq(selected_department)]

    for metric_id, actual_col, target_col, status_col, size_col in [
        ("M13", "attendance_actual", "attendance_target", "Attendance status", None),
        ("M04", "attrition_actual", "attrition_target", "Attrition status", None),
        ("M11", "overtime_actual", "overtime_target", "Overtime status", None),
        ("M22", "task_completion_actual", "task_completion_target", "Task Completion status", "total_tasks"),
    ]:
        direction, minimum = rules[metric_id]
        if metric_id == "M22":
            filtered[status_col] = "🟠 Amber — Team-level actual; department/month comparison unavailable"
        else:
            group_sizes = filtered[size_col] if size_col else pd.Series([minimum] * len(filtered), index=filtered.index)
            filtered[status_col] = [traffic_light(a, t, direction, g, minimum) for a, t, g in zip(filtered[actual_col], filtered[target_col], group_sizes)]

    st.subheader("KPI Traffic Lights")
    display = filtered[["month", "department_id", "attendance_actual", "attendance_target", "Attendance status", "attrition_actual", "attrition_target", "Attrition status", "overtime_actual", "overtime_target", "Overtime status", "task_completion_actual", "task_completion_target", "total_tasks", "completed_tasks", "Task Completion status"]].copy()
    display.rename(columns={"month": "Month", "department_id": "Department", "attendance_actual": "Attendance Actual (%)", "attendance_target": "Attendance Target (%)", "attrition_actual": "Attrition Actual (%)", "attrition_target": "Attrition Target (%)", "overtime_actual": "Overtime Actual (%)", "overtime_target": "Overtime Target (%)", "task_completion_actual": "Task Completion Actual (%)", "task_completion_target": "Task Completion Target (%)", "total_tasks": "Total Tasks", "completed_tasks": "Completed Tasks"}, inplace=True)
    for col in ["Attendance Actual (%)", "Attendance Target (%)", "Attrition Actual (%)", "Attrition Target (%)", "Overtime Actual (%)", "Overtime Target (%)", "Task Completion Actual (%)", "Task Completion Target (%)"]:
        display[col] = pd.to_numeric(display[col], errors="coerce").round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("Traffic-light directions and minimum group sizes follow the exported metric catalog where available. Task completion is shown separately because its source is team-level, not department/month-level.")

    st.subheader("Team Task Completion (Overall Exported Period)")
    if not task_team_display.empty:
        st.metric("Overall Task Completion", f"{overall_task_completion:.2f}%" if pd.notna(overall_task_completion) else "Not available")
        st.dataframe(task_team_display, use_container_width=True, hide_index=True)
        st.caption("Task completion is calculated from completed_tasks / total_tasks across teams. It is not assigned to departments or months because those dimensions are absent from the exported source.")
    else:
        st.info("No valid team task-completion records are available.")

    st.subheader("Department Ranking by Overspend")
    budget = load_parquet("metric_budget_payroll_dept_month")
    payroll = load_parquet("metric_m09_payroll_cost")
    budget = standardize_month(budget, ["month", "month_start_date", "period_end_date"])
    budget = standardize_department(budget)
    budget_col = first_column(budget, ["budget_payroll_cost", "budget", "budget_amount"])
    budget["budget"] = pd.to_numeric(budget[budget_col], errors="coerce")
    payroll = standardize_month(payroll, ["period_end_date", "month_start_date", "month"])
    payroll = standardize_department(payroll)
    actual_col = first_column(payroll, ["employer_cost", "payroll_cost", "actual"])
    payroll["actual"] = pd.to_numeric(payroll[actual_col], errors="coerce")
    budget_monthly = budget.groupby(["month", "department_id"], as_index=False)["budget"].sum()
    actual_monthly = payroll.groupby(["month", "department_id"], as_index=False)["actual"].sum()
    monthly = budget_monthly.merge(actual_monthly, on=["month", "department_id"], how="inner")
    ranking = monthly.groupby("department_id", as_index=False).agg(total_budget=("budget", "sum"), total_actual=("actual", "sum"))
    ranking["variance"] = ranking["total_actual"] - ranking["total_budget"]
    ranking["variance_pct"] = (100 * ranking["variance"] / ranking["total_budget"].replace(0, pd.NA)).round(2)
    ranking["comparable_months"] = monthly.groupby("department_id").size().reindex(ranking["department_id"]).to_numpy()
    ranking = ranking.sort_values("variance", ascending=False).reset_index(drop=True)
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    for col in ["total_budget", "total_actual", "variance"]:
        ranking[col] = ranking[col].round(2)
    st.caption("Positive variance indicates overspend. Negative variance indicates underspend. Ranking uses months where both budget and governed actual payroll cost are available.")
    st.dataframe(ranking, use_container_width=True, hide_index=True)

except Exception as exc:
    st.error(f"Unable to load KPI traffic lights: {exc}")
