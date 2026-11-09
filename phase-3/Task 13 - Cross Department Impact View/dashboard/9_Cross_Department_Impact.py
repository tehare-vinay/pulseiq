import os
from pathlib import Path
import pandas as pd
import psycopg2
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

# Load project environment variables
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="Cross Department Impact",
    page_icon="📊",
    layout="wide"
)

st.title("Cross-Department Impact View")
st.caption("Task 13 | Department-wise payroll cost, overtime and attrition")

st.info(
    "This view compares employer cost, overtime cost and average monthly "
    "attrition across departments using the Task 13 department-month comparison."
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
def load_department_comparison():
    query = """
    WITH payroll_monthly AS (
        SELECT
            department_id,
            DATE_TRUNC(
                'month', period_end_date::timestamp
            )::date AS month_start,
            SUM(employer_cost::numeric) AS employer_cost,
            SUM(overtime_pay::numeric) AS overtime_cost
        FROM fact_payroll
        WHERE DATE_TRUNC(
            'month', period_end_date::timestamp
        )::date >= DATE '2025-04-01'
        GROUP BY
            department_id,
            DATE_TRUNC('month', period_end_date::timestamp)::date
    ),

    headcount_monthly AS (
        SELECT
            department_id,
            month_start_date::timestamp::date AS month_start,
            MAX(attrition_rate_monthly_pct::numeric)
                AS attrition_rate_monthly_pct
        FROM fact_headcount_monthly
        WHERE month_start_date::timestamp::date >= DATE '2025-04-01'
        GROUP BY
            department_id,
            month_start_date::timestamp::date
    ),

    monthly_comparison AS (
        SELECT
            h.department_id,
            h.month_start,
            p.employer_cost,
            p.overtime_cost,
            h.attrition_rate_monthly_pct
        FROM headcount_monthly h
        INNER JOIN payroll_monthly p
            ON p.department_id = h.department_id
           AND p.month_start = h.month_start
    )

    SELECT
        d.department_id,
        d.department_name,
        COUNT(*) AS months_compared,
        ROUND(SUM(m.employer_cost), 2) AS total_employer_cost,
        ROUND(SUM(m.overtime_cost), 2) AS total_overtime_cost,
        ROUND(AVG(m.attrition_rate_monthly_pct), 2)
            AS avg_monthly_attrition_pct
    FROM monthly_comparison m
    JOIN dim_department d
        ON d.department_id = m.department_id
    GROUP BY
        d.department_id,
        d.department_name
    ORDER BY d.department_id;
    """

    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


try:
    df = load_department_comparison()

    if df.empty:
        st.warning("No department comparison data is available.")
        st.stop()

    # Numeric conversion
    numeric_columns = [
        "months_compared",
        "total_employer_cost",
        "total_overtime_cost",
        "avg_monthly_attrition_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # KPI cards
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Departments Compared",
        f"{df['department_id'].nunique()}"
    )

    col2.metric(
        "Months Compared",
        f"{int(df['months_compared'].min())}–"
        f"{int(df['months_compared'].max())}"
    )

    col3.metric(
        "Total Employer Cost",
        f"₹{df['total_employer_cost'].sum():,.2f}"
    )

    st.divider()

    st.subheader("Department Comparison")

    # Combined chart: cost bars + attrition line
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["department_name"],
            y=df["total_employer_cost"],
            name="Employer Cost",
            yaxis="y",
            hovertemplate=(
                "%{x}<br>Employer Cost: ₹%{y:,.2f}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["department_name"],
            y=df["total_overtime_cost"],
            name="Overtime Cost",
            yaxis="y",
            hovertemplate=(
                "%{x}<br>Overtime Cost: ₹%{y:,.2f}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["department_name"],
            y=df["avg_monthly_attrition_pct"],
            name="Average Monthly Attrition",
            yaxis="y2",
            mode="lines+markers",
            hovertemplate=(
                "%{x}<br>Average Attrition: %{y:.2f}%<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        barmode="group",
        height=600,
        xaxis=dict(
            title="Department",
            tickangle=-35
        ),
        yaxis=dict(
            title="Cost (₹)",
            tickformat=",.0f"
        ),
        yaxis2=dict(
            title="Average Monthly Attrition (%)",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=40, r=60, t=80, b=120),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Employer cost and overtime cost use the left axis. "
        "Average monthly attrition uses the right axis."
    )

    # Numeric findings
    st.subheader("Key Department Findings")

    highest_cost = df.loc[df["total_employer_cost"].idxmax()]
    highest_overtime = df.loc[df["total_overtime_cost"].idxmax()]
    highest_attrition = df.loc[
        df["avg_monthly_attrition_pct"].idxmax()
    ]

    st.markdown(
        f"- **Highest employer cost:** "
        f"{highest_cost['department_name']} "
        f"(₹{highest_cost['total_employer_cost']:,.2f})"
    )

    st.markdown(
        f"- **Highest overtime cost:** "
        f"{highest_overtime['department_name']} "
        f"(₹{highest_overtime['total_overtime_cost']:,.2f})"
    )

    st.markdown(
        f"- **Highest average monthly attrition:** "
        f"{highest_attrition['department_name']} "
        f"({highest_attrition['avg_monthly_attrition_pct']:.2f}%)"
    )

    st.divider()

    st.subheader("Department Comparison Data")

    display_df = df.rename(columns={
        "department_id": "Department ID",
        "department_name": "Department",
        "months_compared": "Months Compared",
        "total_employer_cost": "Total Employer Cost",
        "total_overtime_cost": "Total Overtime Cost",
        "avg_monthly_attrition_pct": "Avg Monthly Attrition (%)",
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # Download comparison output
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Department Comparison CSV",
        data=csv,
        file_name="task13_department_comparison.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error("Unable to load Task 13 department comparison.")
    st.exception(e)
