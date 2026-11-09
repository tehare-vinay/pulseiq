
import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="Payroll Cost Dashboard",
    page_icon="💰",
    layout="wide"
)

st.title("Payroll Cost Dashboard")
st.caption("Task 9 | Department and monthly payroll cost analysis")

st.info(
    "This dashboard displays aggregated governed payroll metrics only. "
    "Individual employee salary details are never displayed."
)


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


def load_payroll_metrics():
    gross = read_query("""
        SELECT period_end_date, department_id, gross_pay
        FROM public.metric_m07_gross_pay
    """)

    net = read_query("""
        SELECT period_end_date, department_id, net_pay
        FROM public.metric_m08_net_pay
    """)

    employer = read_query("""
        SELECT period_end_date, department_id, employer_cost
        FROM public.metric_m09_payroll_cost
    """)

    cost_head = read_query("""
        SELECT period_end_date, department_id, cost_per_head
        FROM public.metric_m10_cost_per_head
    """)

    return gross, net, employer, cost_head


try:
    gross, net, employer, cost_head = load_payroll_metrics()

    frames = [gross, net, employer, cost_head]

    for frame in frames:
        frame["period_end_date"] = pd.to_datetime(
            frame["period_end_date"], errors="coerce"
        )

    # Merge governed metric views
    payroll = gross.merge(
        net,
        on=["period_end_date", "department_id"],
        how="outer"
    )

    payroll = payroll.merge(
        employer,
        on=["period_end_date", "department_id"],
        how="outer"
    )

    payroll = payroll.merge(
        cost_head,
        on=["period_end_date", "department_id"],
        how="outer"
    )

    payroll = payroll.dropna(subset=["period_end_date"])

    if payroll.empty:
        st.warning("No governed payroll metric data is available.")
        st.stop()

    payroll["month"] = (
        payroll["period_end_date"].dt.to_period("M").astype(str)
    )

    # Filters
    st.subheader("Payroll Filters")

    c1, c2 = st.columns(2)

    months = sorted(payroll["month"].dropna().unique().tolist())

    departments = sorted(
        payroll["department_id"].dropna().astype(str).unique().tolist()
    )

    with c1:
        selected_month = st.selectbox(
            "Select Month",
            ["All months"] + months
        )

    with c2:
        selected_department = st.selectbox(
            "Select Department",
            ["All departments"] + departments
        )

    filtered = payroll.copy()

    if selected_month != "All months":
        filtered = filtered[
            filtered["month"] == selected_month
        ]

    if selected_department != "All departments":
        filtered = filtered[
            filtered["department_id"].astype(str)
            == selected_department
        ]

    if filtered.empty:
        st.warning("No records available for the selected filters.")
        st.stop()

    # KPI summaries
    st.subheader("Payroll Summary")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Gross Pay",
        f"₹{filtered['gross_pay'].sum():,.2f}"
    )

    c2.metric(
        "Net Pay",
        f"₹{filtered['net_pay'].sum():,.2f}"
    )

    c3.metric(
        "Employer Cost",
        f"₹{filtered['employer_cost'].sum():,.2f}"
    )

    # Department and monthly breakdown
    st.subheader("Department-wise Monthly Payroll Breakdown")

    breakdown = filtered[
        [
            "month",
            "department_id",
            "gross_pay",
            "net_pay",
            "employer_cost",
        ]
    ].sort_values(["month", "department_id"])

    st.dataframe(
        breakdown.rename(columns={
            "month": "Month",
            "department_id": "Department",
            "gross_pay": "Gross Pay (₹)",
            "net_pay": "Net Pay (₹)",
            "employer_cost": "Employer Cost (₹)",
        }),
        use_container_width=True,
        hide_index=True
    )

    # Department-wise employer cost
    st.subheader("Department-wise Employer Cost")

    dept_cost = (
        filtered.groupby("department_id", as_index=False)
        ["employer_cost"].sum()
        .sort_values("employer_cost", ascending=False)
    )

    st.bar_chart(
        dept_cost.set_index("department_id")["employer_cost"],
        y_label="Employer Cost (₹)"
    )

    # Monthly payroll trend
    st.subheader("Monthly Payroll Cost Trend")

    monthly = (
        filtered.groupby("period_end_date", as_index=False)
        [["gross_pay", "net_pay", "employer_cost"]]
        .sum()
        .sort_values("period_end_date")
    )

    trend = monthly.rename(columns={
        "gross_pay": "Gross Pay",
        "net_pay": "Net Pay",
        "employer_cost": "Employer Cost",
    })

    st.line_chart(
        trend.set_index("period_end_date"),
        y_label="Amount (₹)"
    )

    # Cost per employee - department-wise monthly trend
    st.subheader("Cost per Employee")

    head_monthly = cost_head.copy()

    head_monthly["month"] = (
        head_monthly["period_end_date"]
        .dt.to_period("M").astype(str)
    )

    if selected_month != "All months":
        head_monthly = head_monthly[
            head_monthly["month"] == selected_month
        ]

    if selected_department != "All departments":
        head_monthly = head_monthly[
            head_monthly["department_id"].astype(str)
            == selected_department
        ]

    head_trend = (
        head_monthly.pivot_table(
            index="period_end_date",
            columns="department_id",
            values="cost_per_head",
            aggfunc="first"
        )
        .sort_index()
    )

    st.line_chart(
        head_trend,
        y_label="Cost per Employee (₹)"
    )

    st.caption(
        "All figures are aggregated governed metrics. "
        "Groups below five distinct employees are suppressed "
        "by the underlying metric views."
    )

except Exception as exc:
    st.error("Payroll metrics could not be loaded.")
    st.code(str(exc))
