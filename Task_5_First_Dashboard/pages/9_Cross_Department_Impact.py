from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Resolve the project root from:
# Task 5 - First Dashboard/pages/9_Cross_Department_Impact.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARQUET_DIR = PROJECT_ROOT / "cloud_data_parquet"

st.set_page_config(
    page_title="Cross Department Impact",
    page_icon="📊",
    layout="wide",
)

st.title("Cross-Department Impact View")
st.caption("Task 13 | Department-wise payroll cost, overtime and attrition")

st.info(
    "This view compares employer cost, overtime hours and average monthly "
    "attrition across departments using the exported department-level data. "
    "Department IDs are shown because department names are not included in "
    "the available cloud exports."
)


@st.cache_data(ttl=300)
def load_parquet(dataset_name: str) -> pd.DataFrame:
    # Only allow a plain dataset name; prevent path traversal.
    if not dataset_name.replace("_", "").isalnum():
        raise ValueError("Invalid dataset name.")
    file_path = PARQUET_DIR / f"{dataset_name}.parquet"
    if not file_path.is_file():
        raise FileNotFoundError(f"Parquet dataset not found: {file_path.name}")
    return pd.read_parquet(file_path)


@st.cache_data(ttl=300)
def load_department_comparison() -> pd.DataFrame:
    payroll = load_parquet("cloud_payroll_monthly_department")
    headcount = load_parquet("cloud_headcount_monthly_department")

    payroll_required = {
        "period_end_date", "department_id", "employer_cost", "overtime_hours"
    }
    headcount_required = {
        "month_start_date", "department_id", "headcount_start", "exits"
    }

    missing_payroll = payroll_required.difference(payroll.columns)
    missing_headcount = headcount_required.difference(headcount.columns)
    if missing_payroll:
        raise ValueError(f"Payroll export missing columns: {sorted(missing_payroll)}")
    if missing_headcount:
        raise ValueError(f"Headcount export missing columns: {sorted(missing_headcount)}")

    payroll["month_start"] = (
        pd.to_datetime(payroll["period_end_date"], errors="coerce")
        .dt.to_period("M").dt.to_timestamp()
    )
    headcount["month_start"] = (
        pd.to_datetime(headcount["month_start_date"], errors="coerce")
        .dt.to_period("M").dt.to_timestamp()
    )

    payroll["department_id"] = payroll["department_id"].astype("string")
    headcount["department_id"] = headcount["department_id"].astype("string")

    for col in ["employer_cost", "overtime_hours"]:
        payroll[col] = pd.to_numeric(payroll[col], errors="coerce").fillna(0)

    for col in ["headcount_start", "exits"]:
        headcount[col] = pd.to_numeric(headcount[col], errors="coerce")

    payroll_monthly = (
        payroll.loc[payroll["month_start"] >= pd.Timestamp("2025-04-01")]
        .groupby(["department_id", "month_start"], as_index=False)
        .agg(
            employer_cost=("employer_cost", "sum"),
            overtime_hours=("overtime_hours", "sum"),
        )
    )

    headcount_monthly = (
        headcount.loc[headcount["month_start"] >= pd.Timestamp("2025-04-01")]
        .groupby(["department_id", "month_start"], as_index=False)
        .agg(
            headcount_start=("headcount_start", "sum"),
            exits=("exits", "sum"),
        )
    )

    # Calculate a monthly rate from the available aggregate fields.
    # Months with zero/missing starting headcount are excluded from the rate.
    headcount_monthly["attrition_rate_monthly_pct"] = (
        headcount_monthly["exits"]
        .div(headcount_monthly["headcount_start"].where(
            headcount_monthly["headcount_start"] > 0
        ))
        .mul(100)
    )

    monthly = payroll_monthly.merge(
        headcount_monthly,
        on=["department_id", "month_start"],
        how="inner",
        validate="one_to_one",
    )

    if monthly.empty:
        return pd.DataFrame()

    result = (
        monthly.groupby("department_id", as_index=False)
        .agg(
            months_compared=("month_start", "nunique"),
            total_employer_cost=("employer_cost", "sum"),
            total_overtime_hours=("overtime_hours", "sum"),
            avg_monthly_attrition_pct=("attrition_rate_monthly_pct", "mean"),
        )
        .sort_values("department_id")
    )

    result["total_employer_cost"] = result["total_employer_cost"].round(2)
    result["total_overtime_hours"] = result["total_overtime_hours"].round(2)
    result["avg_monthly_attrition_pct"] = (
        result["avg_monthly_attrition_pct"].round(2)
    )
    result["department_name"] = result["department_id"]
    return result


try:
    df = load_department_comparison()

    if df.empty:
        st.warning("No department comparison data is available for matching months.")
        st.stop()

    numeric_columns = [
        "months_compared",
        "total_employer_cost",
        "total_overtime_hours",
        "avg_monthly_attrition_pct",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    col1, col2, col3 = st.columns(3)
    col1.metric("Departments Compared", f"{df['department_id'].nunique()}")
    col2.metric(
        "Months Compared",
        f"{int(df['months_compared'].min())}–{int(df['months_compared'].max())}",
    )
    col3.metric("Total Employer Cost", f"₹{df['total_employer_cost'].sum():,.2f}")

    st.divider()
    st.subheader("Department Comparison")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["department_name"],
            y=df["total_employer_cost"],
            name="Employer Cost",
            yaxis="y",
            hovertemplate="%{x}<br>Employer Cost: ₹%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["department_name"],
            y=df["total_overtime_hours"],
            name="Overtime Hours",
            yaxis="y2",
            hovertemplate="%{x}<br>Overtime Hours: %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["department_name"],
            y=df["avg_monthly_attrition_pct"],
            name="Average Monthly Attrition",
            yaxis="y3",
            mode="lines+markers",
            hovertemplate="%{x}<br>Average Attrition: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        height=600,
        xaxis=dict(title="Department ID", tickangle=-35),
        yaxis=dict(title="Employer Cost (₹)", tickformat=",.0f"),
        yaxis2=dict(
            title="Overtime Hours",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        yaxis3=dict(
            title="Average Monthly Attrition (%)",
            overlaying="y",
            side="right",
            anchor="free",
            position=1,
            showgrid=False,
            visible=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=40, r=80, t=80, b=120),
    )
    # Use a secondary right-side axis for attrition, with overtime represented
    # in hover/data table to avoid implying overtime hours are currency.
    fig.update_layout(yaxis3=dict(
        title="Average Monthly Attrition (%)",
        overlaying="y",
        side="right",
        anchor="free",
        position=0.94,
        showgrid=False,
        visible=True,
    ))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Employer cost is shown in rupees. Overtime is shown in hours, not cost, "
        "because the exported Parquet data does not contain overtime_pay. "
        "Average monthly attrition is calculated as exits ÷ starting headcount × 100 "
        "for matched department-months."
    )

    st.subheader("Key Department Findings")
    highest_cost = df.loc[df["total_employer_cost"].idxmax()]
    highest_overtime = df.loc[df["total_overtime_hours"].idxmax()]
    attrition_df = df.dropna(subset=["avg_monthly_attrition_pct"])

    st.markdown(
        f"- **Highest employer cost:** {highest_cost['department_id']} "
        f"(₹{highest_cost['total_employer_cost']:,.2f})"
    )
    st.markdown(
        f"- **Highest overtime hours:** {highest_overtime['department_id']} "
        f"({highest_overtime['total_overtime_hours']:,.2f} hours)"
    )
    if not attrition_df.empty:
        highest_attrition = attrition_df.loc[
            attrition_df["avg_monthly_attrition_pct"].idxmax()
        ]
        st.markdown(
            f"- **Highest average monthly attrition:** "
            f"{highest_attrition['department_id']} "
            f"({highest_attrition['avg_monthly_attrition_pct']:.2f}%)"
        )
    else:
        st.markdown("- **Highest average monthly attrition:** Not available")

    st.divider()
    st.subheader("Department Comparison Data")

    display_df = df.rename(columns={
        "department_id": "Department ID",
        "months_compared": "Months Compared",
        "total_employer_cost": "Total Employer Cost (₹)",
        "total_overtime_hours": "Total Overtime Hours",
        "avg_monthly_attrition_pct": "Avg Monthly Attrition (%)",
    })
    display_df = display_df[
        [
            "Department ID",
            "Months Compared",
            "Total Employer Cost (₹)",
            "Total Overtime Hours",
            "Avg Monthly Attrition (%)",
        ]
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Department Comparison CSV",
        data=csv,
        file_name="task13_department_comparison.csv",
        mime="text/csv",
    )

except Exception as e:
    st.error("Unable to load Task 13 department comparison.")
    st.exception(e)
