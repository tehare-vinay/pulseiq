from pathlib import Path
import os

import pandas as pd
import psycopg2
import streamlit as st
st.set_page_config(
    page_title="Profit & Loss",
    layout="wide"
)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.title("Profit & Loss")
st.caption("Monthly P&L | Governed SQL View")

@st.cache_data(ttl=120)
def load_expense_by_category():
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
            SELECT
                category_account,
                category_name,
                bill_count,
                expense_excl_gst,
                gst_amount,
                total_amount
            FROM public.vw_task11_expense_by_category
            ORDER BY expense_excl_gst DESC NULLS LAST
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=120)
def load_top10_vendors():
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
            SELECT
                vendor_rank,
                vendor_id,
                vendor_name,
                bill_count,
                spend_excl_gst,
                total_spend
            FROM public.vw_task11_top10_vendors
            ORDER BY vendor_rank
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=120)
def load_pnl():
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
            'SELECT * FROM public.vw_task11_monthly_pnl ORDER BY month',
            conn
        )
    finally:
        conn.close()

try:
    pnl = load_pnl()
except Exception as exc:
    st.error(f"Unable to load governed P&L view: {exc}")
    st.stop()

if pnl.empty:
    st.warning("No monthly P&L data available.")
    st.stop()

pnl["month"] = pnl["month"].astype(str)
months = pnl["month"].dropna().unique().tolist()

selected_month = st.selectbox(
    "Select month",
    months,
    index=len(months) - 1
)

selected = pnl[pnl["month"] == selected_month].iloc[0]

revenue = float(selected["total_revenue"])
expenses = float(selected["total_expenses"])
profit = float(selected["net_profit"])
margin = float(selected["net_profit_margin_pct"])

def inr(value):
    return f"₹{value:,.2f}"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", inr(revenue))
c2.metric("Total Expenses", inr(expenses))
c3.metric("Net Profit", inr(profit))
c4.metric("Net Profit Margin", f"{margin:.2f}%")

st.subheader(f"Profit & Loss Statement | {selected_month}")

pnl_table = pd.DataFrame({
    "P&L Line Item": [
        "Operating Revenue",
        "Other Income",
        "Total Revenue",
        "Total Expenses",
        "Net Profit",
        "Net Profit Margin"
    ],
    "Amount": [
        inr(float(selected["operating_revenue"])),
        inr(float(selected["other_income"])),
        inr(revenue),
        inr(expenses),
        inr(profit),
        f"{margin:.2f}%"
    ]
})

st.dataframe(pnl_table, use_container_width=True, hide_index=True)

st.subheader("Monthly P&L Trend")
trend = pnl[[
    "month",
    "total_revenue",
    "total_expenses",
    "net_profit"
]].copy()

trend = trend.rename(columns={
    "month": "Month",
    "total_revenue": "Revenue",
    "total_expenses": "Expenses",
    "net_profit": "Net Profit"
})

st.line_chart(trend.set_index("Month"))

st.subheader("Expense Analysis")

try:
    category_data = load_expense_by_category()
    vendor_data = load_top10_vendors()
except Exception as exc:
    st.error(f"Unable to load expense category/vendor views: {exc}")
    st.stop()

category_data = category_data.copy()
vendor_data = vendor_data.copy()

if not category_data.empty:
    category_data["category_label"] = (
        category_data["category_name"]
        .fillna(category_data["category_account"].astype(str))
        .replace("", "Unspecified")
    )
else:
    category_data["category_label"] = pd.Series(dtype="object")

if not vendor_data.empty:
    vendor_data["vendor_label"] = (
        vendor_data["vendor_name"]
        .fillna(vendor_data["vendor_id"].astype(str))
        .replace("", "Unspecified")
    )
else:
    vendor_data["vendor_label"] = pd.Series(dtype="object")

category_col, vendor_col = st.columns(2)

with category_col:
    st.markdown("#### Expense by Category")
    if category_data.empty:
        st.info("No expense category data available.")
    else:
        category_chart = category_data[
            ["category_label", "expense_excl_gst"]
        ].copy()
        category_chart["expense_excl_gst"] = pd.to_numeric(
            category_chart["expense_excl_gst"], errors="coerce"
        ).fillna(0)
        st.bar_chart(
            category_chart.set_index("category_label"),
            y="expense_excl_gst",
            use_container_width=True,
        )
        category_table = category_data[
            [
                "category_label",
                "bill_count",
                "expense_excl_gst",
                "gst_amount",
                "total_amount",
            ]
        ].rename(
            columns={
                "category_label": "Expense Category",
                "bill_count": "Bills",
                "expense_excl_gst": "Expense Excl. GST",
                "gst_amount": "GST",
                "total_amount": "Total Incl. GST",
            }
        )
        st.dataframe(category_table, use_container_width=True, hide_index=True)

with vendor_col:
    st.markdown("#### Top 10 Vendors")
    if vendor_data.empty:
        st.info("No vendor spending data available.")
    else:
        vendor_chart = vendor_data[
            ["vendor_label", "spend_excl_gst"]
        ].copy()
        vendor_chart["spend_excl_gst"] = pd.to_numeric(
            vendor_chart["spend_excl_gst"], errors="coerce"
        ).fillna(0)
        st.bar_chart(
            vendor_chart.set_index("vendor_label"),
            y="spend_excl_gst",
            use_container_width=True,
        )
        vendor_table = vendor_data[
            [
                "vendor_rank",
                "vendor_label",
                "bill_count",
                "spend_excl_gst",
                "total_spend",
            ]
        ].rename(
            columns={
                "vendor_rank": "Rank",
                "vendor_label": "Vendor",
                "bill_count": "Bills",
                "spend_excl_gst": "Spend Excl. GST",
                "total_spend": "Total Spend Incl. GST",
            }
        )
        st.dataframe(vendor_table, use_container_width=True, hide_index=True)

with st.expander("P&L data and governance"):
    st.write("P&L source: public.vw_task11_monthly_pnl")
    st.write("Expense category source: public.vw_task11_expense_by_category")
    st.write("Top vendors source: public.vw_task11_top10_vendors")
    st.write("The page reads governed Task 11 SQL views; it does not query raw fact tables.")
    st.write(f"Available P&L months: {len(months)}")
