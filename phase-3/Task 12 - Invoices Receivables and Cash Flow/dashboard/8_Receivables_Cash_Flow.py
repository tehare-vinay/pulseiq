import os
import streamlit as st
import pandas as pd
import psycopg2

st.set_page_config(
    page_title="Receivables & Cash Flow",
    layout="wide"
)

st.title("Receivables & Cash Flow")
st.caption("Task 12 | Invoice ageing, client payments and cash flow")

st.info(
    """
    **Open Invoice Statuses:** SENT, OVERDUE and PARTIALLY_PAID.

    PAID invoices are closed. CANCELLED and DRAFT invoices are excluded.
    """
)


# Database connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", "")
    )


# Load governed ageing view
@st.cache_data(ttl=60)
def load_ageing_data():
    query = """
        SELECT ageing_bucket, invoice_count, outstanding_amount
        FROM public.vw_task12_receivables_ageing
    """
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


# Load governed client payment view
@st.cache_data(ttl=60)
def load_client_days_to_pay():
    query = """
        SELECT
            client_id,
            client_name,
            paid_invoice_count,
            average_days_to_pay
        FROM public.vw_task12_client_days_to_pay
        ORDER BY average_days_to_pay DESC
    """
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


# --------------------------------------------------
# RECEIVABLES AGEING ANALYSIS
# --------------------------------------------------

st.divider()
st.subheader("Receivables Ageing Analysis")

try:
    df = load_ageing_data()

    bucket_order = [
        "Not yet due",
        "0-30 days",
        "31-60 days",
        "61-90 days",
        "90+ days",
        "Unknown"
    ]

    df = (
        df.set_index("ageing_bucket")
        .reindex(bucket_order, fill_value=0)
        .rename_axis("ageing_bucket")
        .reset_index()
    )

    df["invoice_count"] = pd.to_numeric(
        df["invoice_count"], errors="coerce"
    ).fillna(0)

    df["outstanding_amount"] = pd.to_numeric(
        df["outstanding_amount"], errors="coerce"
    ).fillna(0)

    total_invoices = int(df["invoice_count"].sum())
    total_outstanding = float(df["outstanding_amount"].sum())

    col1, col2 = st.columns(2)

    col1.metric("Open Invoices", f"{total_invoices:,}")
    col2.metric(
        "Total Outstanding",
        f"₹{total_outstanding:,.2f}"
    )

    st.markdown("### Outstanding Amount by Ageing Bucket")

    chart_df = df.set_index("ageing_bucket")[
        "outstanding_amount"
    ]
    st.bar_chart(chart_df)

    st.markdown("### Ageing Bucket Summary")

    display_df = df.copy()
    display_df["outstanding_amount"] = (
        display_df["outstanding_amount"].map(
            lambda x: f"₹{x:,.2f}"
        )
    )

    display_df.columns = [
        "Ageing Bucket",
        "Invoice Count",
        "Outstanding Amount"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Ageing Reconciliation Check")

    check_col1, check_col2 = st.columns(2)

    check_col1.metric(
        "Bucket Invoice Count",
        f"{total_invoices:,}"
    )

    check_col2.metric(
        "Bucket Outstanding Total",
        f"₹{total_outstanding:,.2f}"
    )

    unknown_count = int(
        df.loc[
            df["ageing_bucket"] == "Unknown",
            "invoice_count"
        ].sum()
    )

    if unknown_count == 0:
        st.success(
            "Ageing calculation completed. "
            "No invoices have an unknown ageing bucket."
        )
    else:
        st.warning(
            f"{unknown_count} invoices have an unknown ageing bucket. "
            "Review their due-date information."
        )

except Exception as e:
    st.error(f"Unable to load receivables ageing data: {e}")


# --------------------------------------------------
# CLIENT-WISE AVERAGE DAYS TO PAY
# --------------------------------------------------

st.divider()
st.subheader("Client-wise Average Days to Pay")

st.caption(
    "Average payment time is calculated using PAID invoices only."
)

try:
    client_df = load_client_days_to_pay()

    client_df["average_days_to_pay"] = pd.to_numeric(
        client_df["average_days_to_pay"],
        errors="coerce"
    )

    client_df["paid_invoice_count"] = pd.to_numeric(
        client_df["paid_invoice_count"],
        errors="coerce"
    ).fillna(0)

    client_df = client_df.dropna(
        subset=["average_days_to_pay"]
    )

    client_df = client_df.sort_values(
        "average_days_to_pay",
        ascending=False
    )

    if not client_df.empty:

        slowest_client = client_df.iloc[0]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Clients Analysed",
            f"{len(client_df):,}"
        )

        col2.metric(
            "Highest Average Payment Days",
            f"{slowest_client['average_days_to_pay']:.2f} days"
        )

        col3.metric(
            "Slowest Paying Client",
            slowest_client["client_name"]
        )

        st.markdown("### Top 10 Slowest-Paying Clients")

        top10_df = client_df.head(10).copy()

        chart_df = top10_df.set_index("client_name")[
            "average_days_to_pay"
        ]

        st.bar_chart(chart_df)

        st.markdown("### Client Payment Summary")

        display_client_df = client_df.copy()

        display_client_df["average_days_to_pay"] = (
            display_client_df["average_days_to_pay"].map(
                lambda x: f"{x:.2f} days"
            )
        )

        display_client_df.columns = [
            "Client ID",
            "Client Name",
            "Paid Invoice Count",
            "Average Days to Pay"
        ]

        st.dataframe(
            display_client_df,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            f"Insight: {slowest_client['client_name']} "
            f"has the highest average payment time of "
            f"{slowest_client['average_days_to_pay']:.2f} days."
        )

    else:
        st.warning("No client payment data is available.")

except Exception as e:
    st.error(f"Unable to load client payment data: {e}")

#------------------------------------------
# Monthly Cash In vs Cash Out
#------------------------------------------
st.divider()
st.subheader("Monthly Cash In vs Cash Out")

@st.cache_data(ttl=60)
def load_monthly_cash_flow():
    query = """
        SELECT
            TO_CHAR(month, 'YYYY-MM') AS month,
            cash_in,
            cash_out,
            net_cash_flow
        FROM public.vw_task12_monthly_cash_flow
        ORDER BY month
    """

    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


cash_df = load_monthly_cash_flow()

if not cash_df.empty:
    cash_df = cash_df.set_index("month")

    st.line_chart(
        cash_df[["cash_in", "cash_out"]],
        use_container_width=True
    )

    st.markdown("### Monthly Cash Flow Summary")

    st.dataframe(
        cash_df.reset_index(),
        use_container_width=True,
        hide_index=True
    )

    latest = cash_df.iloc[-1]

    st.info(
        f"Latest month net cash flow: "
        f"₹{latest['net_cash_flow']:,.2f}"
    )
else:
    st.warning("No monthly cash flow data available.")
    
    
# --------------------------------------------------
# TOP OVERDUE CLIENTS
# --------------------------------------------------

st.divider()
st.subheader("Top Overdue Clients")

st.caption(
    "Overdue analysis includes SENT, OVERDUE and PARTIALLY_PAID "
    "invoices with positive overdue days and outstanding balance."
)


@st.cache_data(ttl=60)
def load_overdue_clients():
    query = """
        SELECT
            client_id,
            client_name,
            overdue_invoice_count,
            total_overdue_amount,
            maximum_days_overdue
        FROM public.vw_task12_overdue_clients
        ORDER BY total_overdue_amount DESC
    """

    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


try:
    overdue_df = load_overdue_clients()

    if not overdue_df.empty:

        overdue_df["overdue_invoice_count"] = pd.to_numeric(
            overdue_df["overdue_invoice_count"],
            errors="coerce"
        ).fillna(0)

        overdue_df["total_overdue_amount"] = pd.to_numeric(
            overdue_df["total_overdue_amount"],
            errors="coerce"
        ).fillna(0)

        overdue_df["maximum_days_overdue"] = pd.to_numeric(
            overdue_df["maximum_days_overdue"],
            errors="coerce"
        ).fillna(0)

        total_overdue_clients = len(overdue_df)

        total_overdue_invoices = int(
            overdue_df["overdue_invoice_count"].sum()
        )

        total_overdue_amount = float(
            overdue_df["total_overdue_amount"].sum()
        )

        highest_overdue_client = overdue_df.iloc[0]

        longest_overdue_client = overdue_df.loc[
            overdue_df["maximum_days_overdue"].idxmax()
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Overdue Clients",
            f"{total_overdue_clients:,}"
        )

        col2.metric(
            "Overdue Invoices",
            f"{total_overdue_invoices:,}"
        )

        col3.metric(
            "Total Overdue Amount",
            f"₹{total_overdue_amount:,.2f}"
        )

        st.markdown("### Top 10 Clients by Overdue Amount")

        top_overdue = overdue_df.head(10).copy()

        chart_df = top_overdue.set_index("client_name")[
            "total_overdue_amount"
        ]

        st.bar_chart(chart_df)

        st.markdown("### Overdue Client Summary")

        display_overdue_df = overdue_df.copy()

        display_overdue_df["total_overdue_amount"] = (
            display_overdue_df["total_overdue_amount"].map(
                lambda x: f"₹{x:,.2f}"
            )
        )

        display_overdue_df["maximum_days_overdue"] = (
            display_overdue_df["maximum_days_overdue"].map(
                lambda x: f"{x:,.0f} days"
            )
        )

        display_overdue_df.columns = [
            "Client ID",
            "Client Name",
            "Overdue Invoice Count",
            "Total Overdue Amount",
            "Maximum Days Overdue"
        ]

        st.dataframe(
            display_overdue_df,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            f"Highest overdue amount: "
            f"{highest_overdue_client['client_name']} "
            f"with ₹{highest_overdue_client['total_overdue_amount']:,.2f}."
        )

        st.warning(
            f"Longest overdue duration: "
            f"{longest_overdue_client['client_name']} "
            f"with {longest_overdue_client['maximum_days_overdue']:.0f} days."
        )

    else:
        st.warning("No overdue client records are available.")

except Exception as e:
    st.error(f"Unable to load overdue client data: {e}")
