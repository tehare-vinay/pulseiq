import pandas as pd
import streamlit as st
from cloud_data import load_parquet

st.set_page_config(page_title="Profit & Loss", layout="wide")

st.title("Profit & Loss")
st.caption("Monthly P&L | Governed Parquet Export")

@st.cache_data(ttl=300)
def load_task11_data():
    pnl = load_parquet("vw_task11_monthly_pnl")
    category = load_parquet("vw_task11_expense_by_category")
    vendors = load_parquet("cloud_vendor_spend_summary")
    return pnl, category, vendors

try:
    pnl, category_data, vendor_data = load_task11_data()
except Exception as exc:
    st.error("Unable to load the exported Task 11 Parquet datasets.")
    st.exception(exc)
    st.stop()

if pnl.empty:
    st.warning("No monthly P&L data available.")
    st.stop()

required_pnl = [
    "month", "operating_revenue", "other_income", "total_revenue",
    "total_expenses", "net_profit", "net_profit_margin_pct",
]
missing = [column for column in required_pnl if column not in pnl.columns]
if missing:
    st.error(f"P&L export is missing required columns: {', '.join(missing)}")
    st.stop()

pnl = pnl.copy()
pnl["month"] = pnl["month"].astype(str)
for column in required_pnl[1:]:
    pnl[column] = pd.to_numeric(pnl[column], errors="coerce")
pnl = pnl.dropna(subset=["month"]).sort_values("month")
months = pnl["month"].dropna().unique().tolist()
if not months:
    st.warning("No valid P&L months are available.")
    st.stop()

selected_month = st.selectbox("Select month", months, index=len(months) - 1)
selected_rows = pnl[pnl["month"] == selected_month]
if selected_rows.empty:
    st.warning("No P&L data is available for the selected month.")
    st.stop()
selected = selected_rows.iloc[0]

def inr(value):
    return "Unavailable" if pd.isna(value) else f"₹{value:,.2f}"

revenue = selected["total_revenue"]
expenses = selected["total_expenses"]
profit = selected["net_profit"]
margin = selected["net_profit_margin_pct"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", inr(revenue))
c2.metric("Total Expenses", inr(expenses))
c3.metric("Net Profit", inr(profit))
c4.metric("Net Profit Margin", "Unavailable" if pd.isna(margin) else f"{margin:.2f}%")

st.subheader(f"Profit & Loss Statement | {selected_month}")
pnl_table = pd.DataFrame({
    "P&L Line Item": [
        "Operating Revenue", "Other Income", "Total Revenue",
        "Total Expenses", "Net Profit", "Net Profit Margin",
    ],
    "Amount": [
        inr(selected["operating_revenue"]), inr(selected["other_income"]),
        inr(revenue), inr(expenses), inr(profit),
        "Unavailable" if pd.isna(margin) else f"{margin:.2f}%",
    ],
})
st.dataframe(pnl_table, use_container_width=True, hide_index=True)

st.subheader("Monthly P&L Trend")
trend = pnl[["month", "total_revenue", "total_expenses", "net_profit"]].copy()
trend = trend.rename(columns={
    "month": "Month", "total_revenue": "Revenue",
    "total_expenses": "Expenses", "net_profit": "Net Profit",
})
trend = trend.set_index("Month")
st.line_chart(trend)

st.subheader("Expense Analysis")
category_data = category_data.copy()
vendor_data = vendor_data.copy()

category_required = [
    "category_account", "category_name", "bill_count",
    "expense_excl_gst", "gst_amount", "total_amount",
]
missing = [column for column in category_required if column not in category_data.columns]
if missing:
    st.error(f"Expense category export is missing required columns: {', '.join(missing)}")
    st.stop()

if not category_data.empty:
    category_data["category_label"] = (
        category_data["category_name"].fillna(category_data["category_account"].astype(str))
        .replace("", "Unspecified")
    )
    for column in ["bill_count", "expense_excl_gst", "gst_amount", "total_amount"]:
        category_data[column] = pd.to_numeric(category_data[column], errors="coerce")
else:
    category_data["category_label"] = pd.Series(dtype="object")

vendor_required = ["vendor_count", "bill_count", "total_spend_excl_gst", "total_spend"]
missing = [column for column in vendor_required if column not in vendor_data.columns]
if missing:
    st.error(f"Top vendor export is missing required columns: {', '.join(missing)}")
    st.stop()

if not vendor_data.empty:
    vendor_data["vendor_count"] = pd.to_numeric(vendor_data["vendor_count"], errors="coerce")
    vendor_data["bill_count"] = pd.to_numeric(vendor_data["bill_count"], errors="coerce")
    vendor_data["total_spend_excl_gst"] = pd.to_numeric(vendor_data["total_spend_excl_gst"], errors="coerce")
    vendor_data["total_spend"] = pd.to_numeric(vendor_data["total_spend"], errors="coerce")

category_col, vendor_col = st.columns(2)
with category_col:
    st.markdown("#### Expense by Category")
    if category_data.empty:
        st.info("No expense category data available.")
    else:
        category_chart = category_data[["category_label", "expense_excl_gst"]].copy()
        category_chart["expense_excl_gst"] = category_chart["expense_excl_gst"].fillna(0)
        st.bar_chart(category_chart.set_index("category_label"), y="expense_excl_gst", use_container_width=True)
        category_table = category_data[[
            "category_label", "bill_count", "expense_excl_gst", "gst_amount", "total_amount"
        ]].rename(columns={
            "category_label": "Expense Category", "bill_count": "Bills",
            "expense_excl_gst": "Expense Excl. GST", "gst_amount": "GST",
            "total_amount": "Total Incl. GST",
        })
        st.dataframe(category_table, use_container_width=True, hide_index=True)

with vendor_col:
    st.markdown("#### Vendor Spend Summary (Aggregated)")
    if vendor_data.empty:
        st.info("No vendor spending data available.")
    else:
        vendor_table = vendor_data[[
            "vendor_count", "bill_count", "total_spend_excl_gst", "total_spend"
        ]].rename(columns={
            "vendor_count": "Vendor Count", "bill_count": "Bills",
            "total_spend_excl_gst": "Spend Excl. GST",
            "total_spend": "Total Spend Incl. GST",
        })
        st.dataframe(vendor_table, use_container_width=True, hide_index=True)

with st.expander("P&L data and governance"):
    st.write("P&L source: exported vw_task11_monthly_pnl dataset")
    st.write("Expense category source: exported vw_task11_expense_by_category dataset")
    st.write("Vendor spend source: exported cloud_vendor_spend_summary dataset")
    st.write("The page reads exported governed aggregates, not raw fact tables.")
    st.write(f"Available P&L months: {len(months)}")
    st.write("Vendor-level names and IDs are excluded; only aggregate vendor spend is displayed.")
