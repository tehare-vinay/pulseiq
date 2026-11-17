from pathlib import Path
import pandas as pd

for file in sorted(Path("cloud_data").glob("*.csv")):
    df = pd.read_csv(file, nrows=0)
    columns = list(df.columns)
    sensitive = [
        c for c in columns
        if any(word in c.lower() for word in
               ["employee", "person", "email", "phone", "address",
                "name", "ssn", "salary", "account", "client_id"])
    ]
    print(f"\n{file.name}")
    print("Columns:", ", ".join(columns))
    if sensitive:
        print("REVIEW REQUIRED:", ", ".join(sensitive))
