import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="PulseIQ | Attendance Trends",
    page_icon="📊",
    layout="wide",
)

st.title("Attendance & Leave Trends")
st.caption(
    "Task 6 | Attendance rate by month and department | "
    "Data sourced from the governed metric layer"
)

@st.cache_data(ttl=120)
def load_attendance():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )
    try:
        return pd.read_sql_query(
            """
            SELECT period_end_date, department_id, attendance_rate_pct
            FROM public.metric_m13_attendance_rate
            ORDER BY period_end_date, department_id
            """,
            conn,
        )
    finally:
        conn.close()

try:
    df = load_attendance()
except Exception as exc:
    st.error("Could not read the governed attendance metric view.")
    st.code(str(exc))
    st.stop()

required = {"period_end_date", "department_id", "attendance_rate_pct"}
if not required.issubset(df.columns):
    st.error(
        "The attendance metric view is missing required columns. "
        f"Expected: {sorted(required)}. Found: {list(df.columns)}"
    )
    st.stop()

if df.empty:
    st.warning("The attendance metric view returned no rows.")
    st.stop()

df["period_end_date"] = pd.to_datetime(
    df["period_end_date"], errors="coerce"
)
df["attendance_rate_pct"] = pd.to_numeric(
    df["attendance_rate_pct"], errors="coerce"
)
df["department_id"] = df["department_id"].astype(str)
df = df.dropna(
    subset=["period_end_date", "attendance_rate_pct", "department_id"]
).copy()
df["month"] = df["period_end_date"].dt.strftime("%Y-%m")

if df.empty:
    st.warning("No valid attendance rows are available after type checks.")
    st.stop()

st.subheader("Filters")
f1, f2, f3 = st.columns(3)

departments = sorted(df["department_id"].unique())
months = sorted(df["month"].unique())

with f1:
    selected_dept = st.selectbox(
        "Department",
        ["All departments"] + departments,
    )
with f2:
    start_month = st.selectbox("From month", months, index=0)
with f3:
    end_month = st.selectbox("To month", months, index=len(months) - 1)

if start_month > end_month:
    st.error("The start month must be before or equal to the end month.")
    st.stop()

view = df[
    (df["month"] >= start_month) &
    (df["month"] <= end_month)
].copy()

if selected_dept != "All departments":
    view = view[view["department_id"] == selected_dept]

if view.empty:
    st.warning("No attendance rows match the selected filters.")
    st.stop()

latest_month = view["month"].max()
latest = view[view["month"] == latest_month]

k1, k2, k3 = st.columns(3)
k1.metric("Departments in selection", f"{view['department_id'].nunique():,}")
k2.metric("Months in selection", f"{view['month'].nunique():,}")
k3.metric(
    f"Mean department rate — {latest_month}",
    f"{latest['attendance_rate_pct'].mean():.2f}%",
)

st.subheader("Monthly attendance rate")
if selected_dept == "All departments":
    trend = (
        view.groupby(["month", "department_id"], as_index=False)
        ["attendance_rate_pct"].mean()
    )
    fig = px.line(
        trend,
        x="month",
        y="attendance_rate_pct",
        color="department_id",
        markers=True,
        title="Attendance rate by month and department",
        labels={
            "month": "Month",
            "attendance_rate_pct": "Attendance rate (%)",
            "department_id": "Department ID",
        },
    )
else:
    trend = (
        view.groupby("month", as_index=False)["attendance_rate_pct"].mean()
        .sort_values("month")
    )
    fig = px.line(
        trend,
        x="month",
        y="attendance_rate_pct",
        markers=True,
        title=f"Monthly attendance — Department {selected_dept}",
        labels={
            "month": "Month",
            "attendance_rate_pct": "Attendance rate (%)",
        },
    )

fig.update_layout(legend_title_text="Department ID")
fig.update_yaxes(ticksuffix="%", rangemode="tozero")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Holiday & Long-weekend calendar")
calendar_path = Path("Task 6 - Attendance and Leave Trends/task6_holiday_long_weekend_summary.csv")
if calendar_path.exists():
    calendar_df = pd.read_csv(calendar_path)
    visible_months = set(view["month"].astype(str).unique())
    calendar_view = calendar_df[
        calendar_df["year_month"].astype(str).isin(visible_months)
    ].copy()

    if not calendar_view.empty:
        calendar_view = calendar_view.rename(columns={
            "year_month": "Month",
            "attendance_rate_pct": "Attendance rate (%)",
            "calendar_working_days": "Calendar working days",
            "weekend_days": "Weekend days",
            "holidays": "Holidays",
            "holiday_long_weekend_candidates": "Holiday / long-weekend candidates",
            "calendar_coverage": "Calendar coverage"
        })
        st.dataframe(
            calendar_view[[
                "Month", "Attendance rate (%)", "Calendar working days",
                "Weekend days", "Holidays",
                "Holiday / long-weekend candidates", "Calendar coverage"
            ]],
            use_container_width=True,
            hide_index=True
        )
        st.caption(
            "Calendar context is shown for the months currently selected. "
            "A holiday or long-weekend candidate is context for interpreting "
            "attendance changes, not proof that it caused a dip."
        )
    else:
        st.info("No calendar rows match the selected attendance months.")
else:
    st.warning("Holiday calendar summary CSV was not found.")


monthly = (
    view.groupby("month", as_index=False)["attendance_rate_pct"]
    .mean()
    .sort_values("month")
)
if len(monthly) >= 2:
    first = monthly.iloc[0]
    last = monthly.iloc[-1]
    change = last["attendance_rate_pct"] - first["attendance_rate_pct"]
    direction = "increased" if change > 0 else "decreased" if change < 0 else "did not change"
    st.markdown(
        f"**Numeric insight:** Mean department attendance {direction} by "
        f"{abs(change):.2f} percentage points, from "
        f"{first['attendance_rate_pct']:.2f}% in {first['month']} to "
        f"{last['attendance_rate_pct']:.2f}% in {last['month']}."
    )
else:
    st.info("Select at least two months to calculate a month-to-month insight.")

st.subheader("Department × month heatmap")
heat = view.pivot_table(
    index="department_id",
    columns="month",
    values="attendance_rate_pct",
    aggfunc="mean",
)
if not heat.empty:
    heat_fig = px.imshow(
        heat,
        aspect="auto",
        color_continuous_scale="RdYlGn",
        labels={
            "x": "Month",
            "y": "Department ID",
            "color": "Attendance rate (%)",
        },
        title="Attendance rate by department and month",
        text_auto=".1f",
    )
    st.plotly_chart(heat_fig, use_container_width=True)
else:
    st.info("Heatmap is unavailable for these filters.")

with st.expander("Metric definition and limitations"):
    st.write(
        "Attendance rate comes from the governed metric_m13_attendance_rate view. "
        "The metric uses scheduled working days as its denominator and includes "
        "the half-day adjustment defined in the source data dictionary."
    )
    st.write(
        "The current metric view exposes department_id rather than department_name, "
        "so department IDs are used as labels. The overall KPI above is the mean "
        "of the department-level rates, not a company-wide weighted attendance rate."
    )
    st.write(
        "Only the approved metric view is queried by this page; raw fact and "
        "dimension tables are not queried by the app."
    )

st.download_button(
    "Download filtered attendance data",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="task6_filtered_attendance.csv",
    mime="text/csv",
)


# ============================================================
# TASK 6 - STEP 3: LATE ARRIVALS, OVERTIME AND LEAVE BY TYPE
# Read only governed metric views.
# ============================================================

@st.cache_data(ttl=120)
def load_task6_step3_metrics():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )
    try:
        late_df = pd.read_sql_query(
            """
            SELECT period_end_date, department_id, late_arrival_rate_pct
            FROM public.metric_m14_late_arrival_rate
            ORDER BY period_end_date, department_id
            """,
            conn,
        )

        overtime_df = pd.read_sql_query(
            """
            SELECT period_end_date, department_id, overtime_hours
            FROM public.metric_m32_overtime_hours
            ORDER BY period_end_date, department_id
            """,
            conn,
        )

        leave_df = pd.read_sql_query(
            """
            SELECT leave_month, leave_type_code, status,
                   leave_requests, employee_count, leave_days
            FROM public.metric_m33_leave_days_by_type_status
            ORDER BY leave_month, leave_type_code, status
            """,
            conn,
        )

        return late_df, overtime_df, leave_df
    finally:
        conn.close()


st.divider()
st.header("Late Arrivals, Overtime & Leave Patterns")

try:
    late_df, overtime_df, leave_df = load_task6_step3_metrics()
except Exception as exc:
    st.error("Could not load one or more governed Task 6 metric views.")
    st.code(str(exc))
    st.stop()


# Normalize date and numeric fields before applying the dashboard filters.
for metric_df in (late_df, overtime_df):
    metric_df["period_end_date"] = pd.to_datetime(
        metric_df["period_end_date"], errors="coerce"
    )
    metric_df["department_id"] = metric_df["department_id"].astype(str)

late_df["late_arrival_rate_pct"] = pd.to_numeric(
    late_df["late_arrival_rate_pct"], errors="coerce"
)
overtime_df["overtime_hours"] = pd.to_numeric(
    overtime_df["overtime_hours"], errors="coerce"
)

late_df["month"] = late_df["period_end_date"].dt.strftime("%Y-%m")
overtime_df["month"] = overtime_df["period_end_date"].dt.strftime("%Y-%m")

late_filtered = late_df[
    late_df["month"].between(start_month, end_month)
].copy()
overtime_filtered = overtime_df[
    overtime_df["month"].between(start_month, end_month)
].copy()

if selected_dept != "All departments":
    late_filtered = late_filtered[
        late_filtered["department_id"] == selected_dept
    ]
    overtime_filtered = overtime_filtered[
        overtime_filtered["department_id"] == selected_dept
    ]


# 1. Late-arrival rate by month and department
st.subheader("1. Late-arrival rate")

if not late_filtered.empty:
    late_monthly = (
        late_filtered.groupby(
            ["month", "department_id"], as_index=False
        )["late_arrival_rate_pct"].mean()
    )

    late_fig = px.line(
        late_monthly,
        x="month",
        y="late_arrival_rate_pct",
        color="department_id" if selected_dept == "All departments" else None,
        markers=True,
        title="Late arrivals as a percentage of scheduled days",
        labels={
            "month": "Month",
            "late_arrival_rate_pct": "Late-arrival rate (%)",
            "department_id": "Department ID",
        },
    )
    late_fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(late_fig, use_container_width=True)

    peak_late = late_monthly.loc[
        late_monthly["late_arrival_rate_pct"].idxmax()
    ]
    st.markdown(
        f"**Numeric insight:** The highest displayed department-month "
        f"late-arrival rate was {peak_late['late_arrival_rate_pct']:.2f}% "
        f"in {peak_late['month']} (department {peak_late['department_id']})."
    )
else:
    st.info("No late-arrival metric rows match these filters.")


# 2. Overtime hours by month and department
st.subheader("2. Overtime hours")

if not overtime_filtered.empty:
    overtime_monthly = (
        overtime_filtered.groupby(
            ["month", "department_id"], as_index=False
        )["overtime_hours"].sum()
    )

    overtime_fig = px.bar(
        overtime_monthly,
        x="month",
        y="overtime_hours",
        color="department_id" if selected_dept == "All departments" else None,
        barmode="group",
        title="Recorded attendance overtime hours",
        labels={
            "month": "Month",
            "overtime_hours": "Overtime hours",
            "department_id": "Department ID",
        },
    )
    st.plotly_chart(overtime_fig, use_container_width=True)

    peak_overtime = overtime_monthly.loc[
        overtime_monthly["overtime_hours"].idxmax()
    ]
    st.markdown(
        f"**Numeric insight:** The highest displayed department-month "
        f"overtime total was {peak_overtime['overtime_hours']:.1f} hours "
        f"in {peak_overtime['month']} (department "
        f"{peak_overtime['department_id']})."
    )
else:
    st.info("No overtime metric rows match these filters.")


# 3. Leave days by leave type and status
st.subheader("3. Leave days by type and status")


if not leave_df.empty:
    leave_df["leave_month"] = leave_df["leave_month"].astype(str).str[:7]
    leave_df["leave_days"] = pd.to_numeric(
        leave_df["leave_days"], errors="coerce"
    )
    leave_df["leave_requests"] = pd.to_numeric(
        leave_df["leave_requests"], errors="coerce"
    )

    leave_filtered = leave_df[
        leave_df["leave_month"].between(start_month, end_month)
    ].copy()

    if not leave_filtered.empty:
        leave_summary = (
            leave_filtered.groupby(
                ["leave_type_code", "status"], as_index=False
            )["leave_days"].sum()
        )

        leave_fig = px.bar(
            leave_summary,
            x="leave_type_code",
            y="leave_days",
            color="status",
            barmode="group",
            title="Leave days by leave type and status",
            labels={
                "leave_type_code": "Leave type",
                "leave_days": "Leave days",
                "status": "Leave status",
            },
        )
        st.plotly_chart(leave_fig, use_container_width=True)

        top_leave = leave_summary.loc[
            leave_summary["leave_days"].idxmax()
        ]
        st.markdown(
            f"**Numeric insight:** The largest leave-type/status total in "
            f"the selected period was {top_leave['leave_days']:.1f} days "
            f"for type {top_leave['leave_type_code']} "
            f"({top_leave['status']})."
        )
    else:
        st.info("No leave metric rows match the selected month range.")
else:
    st.info("The governed leave metric view returned no rows.")

with st.expander("Step 3 metric notes"):
    st.write(
        "Late-arrival rate is sourced from metric_m14_late_arrival_rate. "
        "Overtime hours are sourced from metric_m32_overtime_hours, which "
        "uses the attendance dataset rather than payroll overtime."
    )
    st.write(
        "Leave days are sourced from metric_m33_leave_days_by_type_status. "
        "That view does not expose department_id, so the leave chart can be "
        "filtered by month range but not by department. Do not interpret "
        "it as a department-specific leave breakdown."
    )
    st.write(
        "These visuals show aggregate metric values. A metric view's minimum "
        "group-size rule still applies to its underlying rows."
    )
