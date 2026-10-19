from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")

print("\n--- FILES WITH employee_key = -1 ---")

for file_path in raw_dir.glob("*.csv"):
    try:
        df = pd.read_csv(file_path, dtype=str, low_memory=False)

        if "employee_key" in df.columns:
            count = df["employee_key"].fillna("").str.strip().eq("-1").sum()

            if count > 0:
                print(f"{file_path.name}: {count} records")

    except Exception as error:
        print(f"Could not read {file_path.name}: {error}")

print("\n--- DOCUMENTATION REFERENCES ---")

contract_files = list(raw_dir.glob("*data_contracts.csv"))

if contract_files:
    contracts = pd.read_csv(contract_files[0], dtype=str).fillna("")

    mask = contracts.astype(str).apply(
        lambda col: col.str.contains(
            r"employee_key|-1|placeholder|unknown",
            case=False,
            regex=True
        )
    ).any(axis=1)

    print(contracts[mask].to_string(index=False, max_colwidth=80))
else:
    print("data_contracts.csv not found")
    
print("\n--- EMPLOYEE HISTORY CHECK ---")

employee_file = next(raw_dir.glob("*dim_employee.csv"))
payroll_file = next(raw_dir.glob("*fact_payroll.csv"))

employees = pd.read_csv(employee_file, dtype=str).fillna("")
payroll = pd.read_csv(payroll_file, dtype=str).fillna("")

target_ids = ["EMP-9001", "EMP-9002"]

print("\nPayroll records:")
print(
    payroll[payroll["employee_id"].isin(target_ids)][
        ["payroll_item_id", "employee_id", "employee_key", "run_id", "period_end_date"]
    ].to_string(index=False)
)

print("\nMatching employee IDs in employee master:")
matches = employees[employees["employee_id"].isin(target_ids)]

if matches.empty:
    print("No matching employee IDs found in dim_employee.")
else:
    print(
        matches[
            ["employee_key", "employee_id", "valid_from", "valid_to", "is_current"]
        ].to_string(index=False)
    )

print("\n--- CHECK COMPLETE ---")