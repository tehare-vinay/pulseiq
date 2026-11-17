import streamlit as st
import pandas as pd
from cloud_data import load_parquet

st.set_page_config(page_title="Receivables & Cash Flow", layout="wide")
st.title("Receivables & Cash Flow")
st.caption("Task 12 | Invoice ageing, client payments and cash flow")
st.info("**Open Invoice Statuses:** SENT, OVERDUE and PARTIALLY_PAID. PAID invoices are closed. CANCELLED and DRAFT invoices are excluded.")

# Receivables ageing
st.divider()
st.subheader("Receivables Ageing Analysis")
try:
    ageing = load_parquet("vw_task12_receivables_ageing").copy()
    ageing["invoice_count"] = pd.to_numeric(ageing["invoice_count"], errors="coerce").fillna(0)
    ageing["outstanding_amount"] = pd.to_numeric(ageing["outstanding_amount"], errors="coerce").fillna(0)
    order = ["Not yet due", "0-30 days", "31-60 days", "61-90 days", "90+ days", "Unknown"]
    ageing = ageing.set_index("ageing_bucket").reindex(order, fill_value=0).rename_axis("ageing_bucket").reset_index()
    invoice_total = int(ageing["invoice_count"].sum())
    amount_total = float(ageing["outstanding_amount"].sum())
    a, b = st.columns(2)
    a.metric("Open Invoices", f"{invoice_total:,}")
    b.metric("Total Outstanding", f"₹{amount_total:,.2f}")
    st.markdown("### Outstanding Amount by Ageing Bucket")
    st.bar_chart(ageing.set_index("ageing_bucket")["outstanding_amount"])
    shown = ageing.copy()
    shown["outstanding_amount"] = shown["outstanding_amount"].map(lambda x: f"₹{x:,.2f}")
    shown.columns = ["Ageing Bucket", "Invoice Count", "Outstanding Amount"]
    st.markdown("### Ageing Bucket Summary")
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.markdown("### Ageing Reconciliation Check")
    a, b = st.columns(2)
    a.metric("Bucket Invoice Count", f"{invoice_total:,}")
    b.metric("Bucket Outstanding Total", f"₹{amount_total:,.2f}")
    unknown = int(ageing.loc[ageing["ageing_bucket"] == "Unknown", "invoice_count"].sum())
    if unknown == 0:
        st.success("Ageing calculation completed. No invoices have an unknown ageing bucket.")
    else:
        st.warning(f"{unknown} invoices have an unknown ageing bucket. Review their due-date information.")
except Exception as e:
    st.error(f"Unable to load receivables ageing data: {e}")

# Privacy-safe client payment summary
st.divider()
st.subheader("Client Payment Performance")
st.caption("Payment timing is summarized across clients. Individual client names and IDs are not displayed in this public aggregate view.")
try:
    payment = load_parquet("cloud_client_payment_summary").copy()
    cols = ["client_count", "paid_invoice_count", "weighted_avg_days_to_pay", "median_client_avg_days"]
    for col in cols:
        payment[col] = pd.to_numeric(payment[col], errors="coerce")
    payment = payment.dropna(subset=cols)
    if not payment.empty:
        r = payment.iloc[0]
        a, b, c = st.columns(3)
        a.metric("Clients Analysed", f"{int(r['client_count']):,}")
        b.metric("Paid Invoices", f"{int(r['paid_invoice_count']):,}")
        c.metric("Weighted Average Days to Pay", f"{r['weighted_avg_days_to_pay']:.2f} days")
        st.metric("Median Client Average Days to Pay", f"{r['median_client_avg_days']:.2f} days")
        summary = pd.DataFrame({"Metric": ["Clients Analysed", "Paid Invoices", "Weighted Average Days to Pay", "Median Client Average Days to Pay"], "Value": [f"{int(r['client_count']):,}", f"{int(r['paid_invoice_count']):,}", f"{r['weighted_avg_days_to_pay']:.2f} days", f"{r['median_client_avg_days']:.2f} days"]})
        st.markdown("### Client Payment Summary")
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.info(f"Insight: Across {int(r['client_count']):,} clients, weighted average payment time is {r['weighted_avg_days_to_pay']:.2f} days; median client average is {r['median_client_avg_days']:.2f} days.")
    else:
        st.warning("No aggregate client payment data is available.")
except Exception as e:
    st.error(f"Unable to load client payment summary: {e}")

# Monthly cash flow
st.divider()
st.subheader("Monthly Cash In vs Cash Out")
try:
    cash = load_parquet("vw_task12_monthly_cash_flow").copy()
    cash["month"] = pd.to_datetime(cash["month"], errors="coerce")
    for col in ["cash_in", "cash_out", "net_cash_flow"]:
        cash[col] = pd.to_numeric(cash[col], errors="coerce").fillna(0)
    cash = cash.dropna(subset=["month"]).sort_values("month")
    if not cash.empty:
        cash["month_label"] = cash["month"].dt.strftime("%Y-%m")
        st.line_chart(cash.set_index("month_label")[["cash_in", "cash_out"]], use_container_width=True)
        display = cash[["month_label", "cash_in", "cash_out", "net_cash_flow"]].copy()
        display.columns = ["Month", "Cash In", "Cash Out", "Net Cash Flow"]
        st.markdown("### Monthly Cash Flow Summary")
        st.dataframe(display, use_container_width=True, hide_index=True)
        latest = cash.iloc[-1]
        st.info(f"Latest month ({latest['month_label']}) net cash flow: ₹{latest['net_cash_flow']:,.2f}")
    else:
        st.warning("No monthly cash flow data available.")
except Exception as e:
    st.error(f"Unable to load monthly cash flow data: {e}")

# Privacy-safe overdue summary
st.divider()
st.subheader("Overdue Receivables Summary")
st.caption("Overdue analysis includes SENT, OVERDUE and PARTIALLY_PAID invoices with positive overdue days and outstanding balance. Individual client identities are not displayed.")
try:
    overdue = load_parquet("cloud_overdue_summary").copy()
    cols = ["client_count", "overdue_invoice_count", "total_overdue_amount", "maximum_days_overdue"]
    for col in cols:
        overdue[col] = pd.to_numeric(overdue[col], errors="coerce")
    overdue = overdue.dropna(subset=cols)
    if not overdue.empty:
        r = overdue.iloc[0]
        a, b, c = st.columns(3)
        a.metric("Overdue Clients", f"{int(r['client_count']):,}")
        b.metric("Overdue Invoices", f"{int(r['overdue_invoice_count']):,}")
        c.metric("Total Overdue Amount", f"₹{r['total_overdue_amount']:,.2f}")
        a, b = st.columns(2)
        a.metric("Maximum Days Overdue", f"{r['maximum_days_overdue']:,.0f} days")
        b.metric("Average Overdue Invoices per Client", f"{r['overdue_invoice_count'] / r['client_count']:.2f}" if r['client_count'] else "Not available")
        display = pd.DataFrame({"Metric": ["Clients with Overdue Receivables", "Overdue Invoices", "Total Overdue Amount", "Maximum Days Overdue"], "Value": [f"{int(r['client_count']):,}", f"{int(r['overdue_invoice_count']):,}", f"₹{r['total_overdue_amount']:,.2f}", f"{r['maximum_days_overdue']:,.0f} days"]})
        st.markdown("### Overdue Portfolio Summary")
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.warning(f"The overdue portfolio includes {int(r['overdue_invoice_count']):,} invoices across {int(r['client_count']):,} clients, with a maximum overdue duration of {r['maximum_days_overdue']:,.0f} days.")
    else:
        st.warning("No aggregate overdue receivables data is available.")
except Exception as e:
    st.error(f"Unable to load overdue receivables summary: {e}")
