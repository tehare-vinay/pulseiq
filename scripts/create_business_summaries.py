from pathlib import Path
import pandas as pd

private = Path("cloud_data")
public = Path("cloud_data_public")
public.mkdir(exist_ok=True)

# Task 11: Vendor totals without vendor names or IDs
vendors = pd.read_csv(private / "vw_task11_top10_vendors.csv")
vendor_summary = pd.DataFrame([{
    "vendor_count": vendors["vendor_id"].nunique(),
    "bill_count": vendors["bill_count"].sum(),
    "total_spend_excl_gst": vendors["spend_excl_gst"].sum(),
    "total_spend": vendors["total_spend"].sum(),
}])
vendor_summary.to_csv(
    public / "cloud_vendor_spend_summary.csv", index=False
)

# Task 12: Client payment-time summary without client names or IDs
clients = pd.read_csv(private / "vw_task12_client_days_to_pay.csv")
invoice_count = clients["paid_invoice_count"].sum()
weighted_avg = (
    (clients["average_days_to_pay"] * clients["paid_invoice_count"]).sum()
    / invoice_count if invoice_count else 0
)
payment_summary = pd.DataFrame([{
    "client_count": clients["client_id"].nunique(),
    "paid_invoice_count": invoice_count,
    "weighted_avg_days_to_pay": weighted_avg,
    "median_client_avg_days": clients["average_days_to_pay"].median(),
}])
payment_summary.to_csv(
    public / "cloud_client_payment_summary.csv", index=False
)

# Task 12: Overall overdue summary without client names or IDs
overdue = pd.read_csv(private / "vw_task12_overdue_clients.csv")
overdue_summary = pd.DataFrame([{
    "client_count": overdue["client_id"].nunique(),
    "overdue_invoice_count": overdue["overdue_invoice_count"].sum(),
    "total_overdue_amount": overdue["total_overdue_amount"].sum(),
    "maximum_days_overdue": overdue["maximum_days_overdue"].max(),
}])
overdue_summary.to_csv(
    public / "cloud_overdue_summary.csv", index=False
)

print("Anonymous summaries created:")
for name in [
    "cloud_vendor_spend_summary.csv",
    "cloud_client_payment_summary.csv",
    "cloud_overdue_summary.csv",
]:
    print(name, "->", len(pd.read_csv(public / name)), "row(s)")

size = sum(f.stat().st_size for f in public.glob("*.csv"))
print("Public CSV files:", len(list(public.glob("*.csv"))))
print("Total size (MB):", round(size / (1024 * 1024), 3))
