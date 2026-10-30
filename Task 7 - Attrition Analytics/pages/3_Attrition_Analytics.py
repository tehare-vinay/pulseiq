
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Load credentials without hard-coding them. Prefer Task 7's own .env,
# then fall back to project-root and Task 5 .env files if present.
_page_dir = Path(__file__).resolve().parent
_task7_dir = _page_dir.parent
_project_dir = _task7_dir.parent
for _env_path in (
    _task7_dir / ".env",
    _project_dir / ".env",
    _project_dir / "Task 5 - First Dashboard" / ".env",
):
    if _env_path.is_file():
        load_dotenv(_env_path, override=False)

st.set_page_config(
    page_title="PulseIQ | Attrition Analytics",
    page_icon="📉",
    layout="wide",
)

st.title("Attrition Analytics")
st.caption(
    "Task 7 | Actual exits and predicted risk are shown separately. "
    "Data is aggregated to protect individual privacy."
)

MIN_GROUP_SIZE = 10


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


@st.cache_data(ttl=120)
def read_query(query):
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


try:
    # Governed actual-exit metrics
    monthly_exits = read_query("""
        SELECT month_start_date, exits
        FROM public.metric_m03_exits_total
        ORDER BY month_start_date
    """)

    department_exits = read_query("""
        SELECT month_start_date, department_id, exits
        FROM public.metric_m03_exits
        WHERE NULLIF(TRIM(department_id), '') IS NOT NULL
        ORDER BY month_start_date, department_id
    """)

    attrition_rate = read_query("""
        SELECT month_start_date, department_id, attrition_rate_pct
        FROM public.metric_m04_attrition_rate
        WHERE NULLIF(TRIM(department_id), '') IS NOT NULL
        ORDER BY month_start_date, department_id
    """)

    voluntary_exits = read_query("""
        SELECT month_start_date, department_id, voluntary_exits
        FROM public.metric_m06_voluntary_attrition
        WHERE NULLIF(TRIM(department_id), '') IS NOT NULL
        ORDER BY month_start_date, department_id
    """)

    # Aggregate tenure at exit. No employee-level records are displayed.
    tenure = read_query("""
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
    """)

    # Predictions are deliberately aggregated by group, never by person.
    risk = read_query("""
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
    """)

except Exception as exc:
    st.error("Could not load the Task 7 data.")
    st.code(str(exc))
    st.stop()


# Normalise types
for frame, date_column in [
    (monthly_exits, "month_start_date"),
    (department_exits, "month_start_date"),
    (attrition_rate, "month_start_date"),
    (voluntary_exits, "month_start_date"),
]:
    if date_column in frame.columns:
        frame[date_column] = pd.to_datetime(
            frame[date_column], errors="coerce"
        )
        frame.dropna(subset=[date_column], inplace=True)
        frame["month"] = frame[date_column].dt.strftime("%Y-%m")

for frame, columns in [
    (monthly_exits, ["exits"]),
    (department_exits, ["exits"]),
    (attrition_rate, ["attrition_rate_pct"]),
    (voluntary_exits, ["voluntary_exits"]),
    (tenure, ["avg_tenure_days", "exit_records"]),
    (risk, ["prediction_records"]),
]:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

st.subheader("Filters")

all_months = sorted(
    set(monthly_exits.get("month", pd.Series(dtype=str)).dropna())
    | set(department_exits.get("month", pd.Series(dtype=str)).dropna())
)

if not all_months:
    st.warning("No monthly exit data is available.")
    st.stop()

f1, f2 = st.columns(2)
with f1:
    start_month = st.selectbox("From month", all_months, index=0)
with f2:
    end_month = st.selectbox("To month", all_months, index=len(all_months) - 1)

if start_month > end_month:
    st.error("The start month must be before or equal to the end month.")
    st.stop()

monthly_view = monthly_exits[
    monthly_exits["month"].between(start_month, end_month)
].copy()

department_view = department_exits[
    department_exits["month"].between(start_month, end_month)
].copy()

rate_view = attrition_rate[
    attrition_rate["month"].between(start_month, end_month)
].copy()

voluntary_view = voluntary_exits[
    voluntary_exits["month"].between(start_month, end_month)
].copy()


# KPI cards
total_exits = monthly_view["exits"].sum(min_count=1)
mean_rate = rate_view["attrition_rate_pct"].mean()
total_voluntary = voluntary_view["voluntary_exits"].sum(min_count=1)

k1, k2, k3 = st.columns(3)
k1.metric(
    "Exits in selected period",
    "Unavailable" if pd.isna(total_exits) else f"{total_exits:,.0f}",
)
k2.metric(
    "Mean department attrition rate",
    "Unavailable" if pd.isna(mean_rate) else f"{mean_rate:.2f}%",
)
k3.metric(
    "Voluntary exits (metric-view total)",
    "Unavailable" if pd.isna(total_voluntary)
    else f"{total_voluntary:,.0f}",
)
if pd.notna(total_exits) and pd.notna(total_voluntary) and total_voluntary > total_exits:
    st.warning(
        "Data-quality check: voluntary exits exceed total exits for this "
        "selected period. Do not interpret these KPI totals as reconciled; "
        "the source metric definitions/coverage need verification."
    )

st.divider()
st.header("1. Actual exits")

if not monthly_view.empty:
    trend = (
        monthly_view.groupby("month", as_index=False)["exits"]
        .sum(min_count=1)
        .sort_values("month")
    )
    fig = px.bar(
        trend,
        x="month",
        y="exits",
        title="Monthly exits",
        labels={"month": "Month", "exits": "Exits"},
    )
    st.plotly_chart(fig, use_container_width=True)

    valid = trend.dropna(subset=["exits"])
    if not valid.empty:
        peak = valid.loc[valid["exits"].idxmax()]
        st.markdown(
            f"**Numeric insight:** Highest displayed monthly exits were "
            f"{peak['exits']:.0f} in {peak['month']}."
        )

if not department_view.empty:
    st.subheader("Exits by department and month")
    fig = px.bar(
        department_view,
        x="month",
        y="exits",
        color="department_id",
        barmode="group",
        title="Department-wise exits",
        labels={
            "month": "Month",
            "exits": "Exits",
            "department_id": "Department",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        department_view[
            ["month", "department_id", "exits"]
        ].sort_values(["month", "department_id"]),
        use_container_width=True,
        hide_index=True,
    )

if not rate_view.empty:
    st.subheader("Attrition rate by department")
    fig = px.line(
        rate_view,
        x="month",
        y="attrition_rate_pct",
        color="department_id",
        markers=True,
        title="Monthly department attrition rate",
        labels={
            "month": "Month",
            "attrition_rate_pct": "Attrition rate (%)",
            "department_id": "Department",
        },
    )
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("2. Voluntary exits and tenure at exit")

if not voluntary_view.empty:
    voluntary_summary = (
        voluntary_view.groupby("department_id", as_index=False)
        ["voluntary_exits"].sum(min_count=1)
        .sort_values("voluntary_exits", ascending=False)
    )
    fig = px.bar(
        voluntary_summary,
        x="department_id",
        y="voluntary_exits",
        title="Voluntary exits by department",
        labels={
            "department_id": "Department",
            "voluntary_exits": "Voluntary exits",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Other exits are not calculated as total exits minus voluntary exits "
        "unless both metrics have matching definitions and coverage."
    )
else:
    st.info("No voluntary-exit metric rows are available for this period.")

if not tenure.empty:
    st.subheader("Average tenure at exit by department")
    tenure_view = tenure.dropna(subset=["avg_tenure_days"]).copy()

    if not tenure_view.empty:
        fig = px.bar(
            tenure_view,
            x="department_id",
            y="avg_tenure_days",
            title="Average tenure at exit",
            labels={
                "department_id": "Department",
                "avg_tenure_days": "Average tenure (days)",
            },
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            tenure_view[
                ["department_id", "exit_records", "avg_tenure_days"]
            ],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info(
        "No department has enough valid exit-tenure records for this summary."
    )

st.divider()
st.header("3. Predicted, not certain")

st.warning(
    "This section shows model predictions, not confirmed future exits. "
    "Risk scores are not proof that a person will leave and must not be used "
    "alone for employment decisions."
)

if not risk.empty:
    fig = px.bar(
        risk,
        x="department_id",
        y="prediction_records",
        color="risk_band",
        barmode="stack",
        title="Prediction records by department and risk band",
        labels={
            "department_id": "Department",
            "prediction_records": "Prediction records",
            "risk_band": "Predicted risk band",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        risk[
            ["department_id", "risk_band", "prediction_records"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Only department/risk-band groups with at least {MIN_GROUP_SIZE} "
        "prediction records are displayed. Individual names and identifiers "
        "are intentionally excluded."
    )
else:
    st.info(
        "No department/risk-band groups meet the minimum group-size threshold."
    )

st.divider()
st.header("4. Three biggest findings")

findings = []

if not monthly_view.empty:
    valid = monthly_view.dropna(subset=["exits"])
    if not valid.empty:
        peak = valid.loc[valid["exits"].idxmax()]
        findings.append(
            f"Monthly exits peaked at {peak['exits']:.0f} in {peak['month']}."
        )

if not rate_view.empty:
    valid = rate_view.dropna(subset=["attrition_rate_pct"])
    if not valid.empty:
        highest = valid.loc[valid["attrition_rate_pct"].idxmax()]
        findings.append(
            f"Highest available department attrition rate was "
            f"{highest['attrition_rate_pct']:.2f}% for "
            f"{highest['department_id']} in {highest['month']}."
        )

if not voluntary_view.empty:
    valid = voluntary_view.dropna(subset=["voluntary_exits"])
    if not valid.empty:
        summary = valid.groupby("department_id")["voluntary_exits"].sum()
        if not summary.empty:
            dept = summary.idxmax()
            findings.append(
                f"{dept} had the highest displayed voluntary-exit total: "
                f"{summary.loc[dept]:.0f}."
            )

if findings:
    for number, finding in enumerate(findings[:3], start=1):
        st.markdown(f"**{number}.** {finding}")
else:
    st.info("There is not enough valid data to calculate the findings.")

st.divider()
st.subheader("How to interpret predictions")

st.markdown(
    """
    - **Actual exits** describe recorded historical events.
    - **Predicted risk** is a model estimate based on available input data.
    - A prediction is uncertain and does not establish an employee's intent.
    - Small groups are suppressed to reduce the chance of identifying people.
    - Group-level patterns can guide further investigation, not determine
      decisions about an individual.
    """
)
