import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "clean" / "reconciliation_answer_key.csv"

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

sql = """
CREATE TEMP TABLE answer_key (
    month DATE,
    employees_paid NUMERIC,
    payroll_gross_pay NUMERIC,
    payroll_net_pay NUMERIC,
    payroll_employer_cost NUMERIC
);
"""

for r in rows:
    month = r["month"].strip().replace("'", "''")
    sql += (
        "INSERT INTO answer_key VALUES ("
        f"'{month}'::date, "
        f"{float(r['employees_paid'])}, "
        f"{float(r['payroll_gross_pay'])}, "
        f"{float(r['payroll_net_pay'])}, "
        f"{float(r['payroll_employer_cost'])}"
        ");\n"
    )

sql += """
WITH actual AS (
    SELECT
        DATE_TRUNC('month', period_end_date::date)::date AS month,
        COUNT(DISTINCT employee_id) AS employees_paid,
        ROUND(SUM(NULLIF(REGEXP_REPLACE(
            TRIM(gross_pay), '[^0-9.\\-]', '', 'g'
        ), '')::numeric), 2) AS gross,
        ROUND(SUM(NULLIF(REGEXP_REPLACE(
            TRIM(net_pay), '[^0-9.\\-]', '', 'g'
        ), '')::numeric), 2) AS net,
        ROUND(SUM(NULLIF(REGEXP_REPLACE(
            TRIM(employer_cost), '[^0-9.\\-]', '', 'g'
        ), '')::numeric), 2) AS employer_cost
    FROM public.fact_payroll
    GROUP BY DATE_TRUNC('month', period_end_date::date)::date
)
SELECT
    k.month,
    a.employees_paid - k.employees_paid AS employee_diff,
    ROUND(a.gross - k.payroll_gross_pay, 2) AS gross_diff,
    ROUND(a.net - k.payroll_net_pay, 2) AS net_diff,
    ROUND(a.employer_cost - k.payroll_employer_cost, 2)
        AS employer_diff
FROM answer_key k
LEFT JOIN actual a ON a.month = k.month
WHERE a.month IS NULL
   OR a.employees_paid <> k.employees_paid
   OR ABS(a.gross - k.payroll_gross_pay) > 0.01
   OR ABS(a.net - k.payroll_net_pay) > 0.01
   OR ABS(a.employer_cost - k.payroll_employer_cost) > 0.01
ORDER BY k.month;
"""

result = subprocess.run(
    [
        "docker", "exec", "-i", "pulseiq_warehouse_db",
        "psql", "-X", "-P", "pager=off",
        "-U", "pulseiq_user", "-d", "pulseiq_warehouse",
        "-v", "ON_ERROR_STOP=1"
    ],
    input=sql,
    text=True,
    capture_output=True
)

print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    raise SystemExit(result.returncode)