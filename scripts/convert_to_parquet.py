from pathlib import Path
import pandas as pd

source = Path("cloud_data_public")
target = Path("cloud_data_parquet")
target.mkdir(exist_ok=True)

files = sorted(source.glob("*.csv"))

if not files:
    raise SystemExit("ERROR: No public CSV files found.")

for file in files:
    df = pd.read_csv(file)
    output = target / f"{file.stem}.parquet"
    df.to_parquet(output, index=False, engine="pyarrow")

    # Verify that the Parquet file can be reopened
    check = pd.read_parquet(output)
    if len(check) != len(df) or list(check.columns) != list(df.columns):
        raise RuntimeError(f"Verification failed: {file.name}")

    print(f"Verified: {output.name} | {len(check)} rows")

parquet_files = list(target.glob("*.parquet"))
total_bytes = sum(f.stat().st_size for f in parquet_files)

print("\nPARQUET EXPORT VERIFIED")
print("Files:", len(parquet_files))
print("Total size:", round(total_bytes / (1024 * 1024), 3), "MB")
print("Output folder:", target.resolve())
