from pathlib import Path
import shutil

source = Path("cloud_data")
target = Path("cloud_data_public")

excluded = {
    "metric_m21_overdue_receivables.csv",
    "vw_task11_top10_vendors.csv",
    "vw_task12_client_days_to_pay.csv",
    "vw_task12_overdue_clients.csv",
}

target.mkdir(exist_ok=True)

for file in source.glob("*.csv"):
    if file.name not in excluded:
        shutil.copy2(file, target / file.name)

print("Public export files:", len(list(target.glob("*.csv"))))
print("Excluded files:", len(excluded))
print("Public export size (MB):",
      round(sum(f.stat().st_size for f in target.glob("*.csv")) / (1024*1024), 3))
