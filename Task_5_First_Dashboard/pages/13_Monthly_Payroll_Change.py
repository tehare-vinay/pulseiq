import pandas as pd
import streamlit as st
from cloud_data import load_parquet

st.set_page_config(
    page_title="Monthly Payroll Cost Change",
    page_icon="📊",
    layout="wide"
)

st.title("Monthly Payroll Cost Change")
st.caption("Task 20 | Independent Improvement")

st.info(
    "This page compares the latest month's employer payroll cost "
    "with the previous month using governed payroll metrics."
)


@st.cache_data(ttl=300)
def load_payroll_data():
    return load_parquet("metric_m09_payroll_cost")


try:
    payroll = load_payroll_data().copy()

    required_columns = {
        "period_end_date",
        "department_id",
        "employer_cost"
    }

    if not required_columns.issubset(payroll.columns):
        st.error("Required governed payroll columns are missing.")
        st.stop()

    payroll["period_end_date"] = pd.to_datetime(
        payroll["period_end_date"],
        errors="coerce"
    )

    payroll["employer_cost"] = pd.to_numeric(
        payroll["employer_cost"],
        errors="coerce"
    )

    payroll = payroll.dropna(
        subset=["period_end_date", "employer_cost"]
    )

    monthly = (
        payroll.groupby(
            payroll["period_end_date"].dt.to_period("M")
        )["employer_cost"]
        .sum()
        .sort_index()
    )

    if len(monthly) < 2:
        st.warning("At least two months of payroll data are required.")
        st.stop()

    current_month = monthly.index[-1]
    previous_month = monthly.index[-2]

    current_cost = float(monthly.iloc[-1])
    previous_cost = float(monthly.iloc[-2])

    difference = current_cost - previous_cost

    percentage_change = (
        (difference / previous_cost) * 100
        if previous_cost != 0
        else None
    )

    st.subheader("Latest Monthly Comparison")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Latest Month Employer Cost",
        f"₹{current_cost:,.2f}",
        help=str(current_month)
    )

    c2.metric(
        "Previous Month Employer Cost",
        f"₹{previous_cost:,.2f}",
        help=str(previous_month)
    )

    c3.metric(
        "Month-over-Month Change",
        f"₹{difference:,.2f}",
        delta=(
            f"{percentage_change:+.2f}%"
            if percentage_change is not None
            else "Percentage unavailable"
        )
    )

    st.subheader("Monthly Employer Payroll Cost Trend")

    trend = monthly.rename("Employer Cost").reset_index()
    trend.columns = ["Month", "Employer Cost"]
    trend["Month"] = trend["Month"].astype(str)

    st.line_chart(
        trend.set_index("Month"),
        y_label="Employer Cost (₹)"
    )

    st.subheader("Business Insight")

    if difference > 0:
        st.warning(
            f"Employer payroll cost increased by "
            f"₹{difference:,.2f} ({percentage_change:.2f}%) "
            f"from {previous_month} to {current_month}. "
            "Management should review the main cost drivers."
        )
    elif difference < 0:
        st.success(
            f"Employer payroll cost decreased by "
            f"₹{abs(difference):,.2f} "
            f"({abs(percentage_change):.2f}%) "
            f"from {previous_month} to {current_month}."
        )
    else:
        st.info("Employer payroll cost remained unchanged.")

    st.caption(
        "Source: Governed metric_m09_payroll_cost. "
        "Figures are aggregated employer payroll costs."
    )

except Exception as exc:
    st.error("Monthly payroll comparison could not be generated.")
    st.exception(exc)
