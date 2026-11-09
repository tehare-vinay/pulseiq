
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

st.set_page_config(
    page_title="PulseIQ | Attrition Analytics",
    page_icon="ðŸ“‰",
    layout="wide",
)

st.title("Attrition Analytics")
st.caption(
    "Task 7 | Actual exits and predicted risk are shown separately. "
    "Data is aggregated to protect individual privacy."
)

MIN_GROUP_SIZE = 10

st.info(
    "Privacy rule: Departments with fewer than 10 people are not "
    "reported as separate groups. For example, a department with "
    "only 4 people is suppressed, not shown as a separate result "
    "and not treated as zero. Small groups must not be combined "
    "in a way that could identify individuals. Only governed, "
    "privacy-approved aggregate metrics are displayed."
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
        WHERE exits IS NOT NULL
        ORDER BY month_start_date
    """)
   
    department_exits = read_query("""
        SELECT month_start_date, department_id, exits
        FROM public.metric_m03_exits
        WHERE exits IS NOT NULL
        ORDER BY month_start_date, department_id
    """)
    department_totals = read_query("""
    SELECT department_id, exits
    FROM public.metric_m03_exits_by_department
    WHERE exits IS NOT NULL
    ORDER BY department_id
""")
    
    attrition_rate = read_query("""
        SELECT month_start_date, department_id, attrition_rate_pct
        FROM public.metric_m04_attrition_rate
        ORDER BY month_start_date, department_id
    """)

    voluntary_exits = read_query("""
        SELECT month_start_date, department_id, voluntary_exits
        FROM public.metric_m06_voluntary_attrition
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
    "Voluntary exits in selected period",
    "Unavailable" if pd.isna(total_voluntary)
    else f"{total_voluntary:,.0f}",
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
    st.caption(
    "Only monthly exit counts released by the governed metric view are shown. "
    "Suppressed counts are omitted, not treated as zero."
)

    valid = trend.dropna(subset=["exits"])
    if not valid.empty:
        peak = valid.loc[valid["exits"].idxmax()]
        st.markdown(
            f"**Numeric insight:** Highest displayed monthly exits were "
            f"{peak['exits']:.0f} in {peak['month']}."
        )

st.subheader("Total exits by department")

if not department_totals.empty:
    department_totals = department_totals.dropna(
        subset=["department_id", "exits"]
    ).copy()

    fig = px.bar(
        department_totals.sort_values("exits", ascending=False),
        x="department_id",
        y="exits",
        title="Total exits by department — all available months",
        labels={
            "department_id": "Department",
            "exits": "Total exits",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        department_totals.sort_values("exits", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    highest = department_totals.loc[department_totals["exits"].idxmax()]
    st.caption(
        f"Numeric insight: {highest['department_id']} has the highest "
        f"published total exits: {highest['exits']:.0f}."
    )
else:
    st.info("No department-level exit totals meet the publication rules.")
    
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

# Voluntary exits: use the governed metric view as published.
if not voluntary_view.empty:
    voluntary_summary = (
        voluntary_view.groupby("department_id", as_index=False)
        ["voluntary_exits"]
        .sum(min_count=1)
        .dropna(subset=["voluntary_exits"])
        .sort_values("voluntary_exits", ascending=False)
    )

    if not voluntary_summary.empty:
        fig = px.bar(
            voluntary_summary,
            x="department_id",
            y="voluntary_exits",
            title="Published voluntary exits by department",
            labels={
                "department_id": "Department",
                "voluntary_exits": "Voluntary exits",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        highest_voluntary = voluntary_summary.iloc[0]
        st.markdown(
            f"**Numeric insight:** {highest_voluntary['department_id']} "
            f"has the highest published voluntary-exit total: "
            f"{highest_voluntary['voluntary_exits']:.0f}."
        )

        st.dataframe(
            voluntary_summary,
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No published voluntary-exit values are available.")

st.warning(
    "**Other exits: not calculated.** The published voluntary-exit total "
    "does not reconcile with the published total-exit metric for the "
    "selected period. Subtracting these totals could produce a misleading "
    "result. A valid voluntary-versus-other split requires matching "
    "definitions, coverage, and a verified exit-type source."
)

st.caption(
    "Voluntary exits are shown only as published by the governed metric "
    "view. Other exits are not assumed or estimated."
)

# Aggregate tenure: never display individual employee records.
st.subheader("Average tenure at exit by department")

if not tenure.empty:
    tenure_view = tenure.dropna(
        subset=["avg_tenure_days", "exit_records"]
    ).copy()

    if not tenure_view.empty:
        tenure_view = tenure_view.sort_values(
            "avg_tenure_days", ascending=False
        )

        fig = px.bar(
            tenure_view,
            x="department_id",
            y="avg_tenure_days",
            title="Average tenure at exit by department",
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

        longest = tenure_view.iloc[0]
        shortest = tenure_view.iloc[-1]

        st.markdown(
            f"**Numeric insight:** The highest displayed average tenure "
            f"at exit is {longest['avg_tenure_days']:.1f} days "
            f"({longest['department_id']}); the lowest is "
            f"{shortest['avg_tenure_days']:.1f} days "
            f"({shortest['department_id']})."
        )

        st.caption(
            "Tenure is aggregated by department using valid exit records. "
            "Groups with fewer than 10 records are suppressed. "
            "No employee names or individual records are displayed."
        )
    else:
        st.info("No valid tenure-at-exit values are available.")
else:
    st.info(
        "No department has enough valid exit-tenure records for this "
        "summary. Small groups are suppressed to protect privacy."
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
