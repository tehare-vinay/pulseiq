
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "clean" / "reconciliation_answer_key.csv"

# Test-only candidates. These are NOT yet approved permanent exclusions.
CANDIDATE_IDS = [
    "PI-X0002",
    "PI-X0004",
    "PI-X0001",
    "PI-X0003",
]

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

CREATE TEMP TABLE candidate_exclusions (
    payroll_item_id TEXT PRIMARY KEY
);
"""

for r in rows:
    sql += (
        "INSERT INTO answer_key VALUES ("
        f"'{r['month'].strip()}'::date, "
        f"{float(r['employees_paid'])}, "
        f"{float(r['payroll_gross_pay'])}, "
        f"{float(r['payroll_net_pay'])}, "
        f"{float(r['payroll_employer_cost'])}"
        ");\n"
    )

for item_id in CANDIDATE_IDS:
    sql += (
        "INSERT INTO candidate_exclusions VALUES "
        f"('{item_id}');\n"
    )

sql += """
SELECT
    p.payroll_item_id,
    p.period_end_date,
    p.employee_id,
    p.employee_key,
    p.gross_pay,
    p.net_pay,
    p.employer_cost
FROM public.fact_payroll p
JOIN candidate_exclusions x
  ON x.payroll_item_id = p.payroll_item_id
ORDER BY p.period_end_date, p.payroll_item_id;

WITH actual AS (
    SELECT
        DATE_TRUNC('month', p.period_end_date::date)::date AS month,
        COUNT(DISTINCT p.employee_id) AS employees_paid,
        ROUND(SUM(NULLIF(TRIM(p.gross_pay), '')::numeric), 2) AS gross,
        ROUND(SUM(NULLIF(TRIM(p.net_pay), '')::numeric), 2) AS net,
        ROUND(SUM(NULLIF(TRIM(p.employer_cost), '')::numeric), 2)
            AS employer_cost
    FROM public.fact_payroll p
    WHERE NOT EXISTS (
        SELECT 1
        FROM candidate_exclusions x
        WHERE x.payroll_item_id = p.payroll_item_id
    )
    GROUP BY 1
)
SELECT
    k.month,
    COALESCE(a.employees_paid, 0) - k.employees_paid AS employee_diff,
    ROUND(COALESCE(a.gross, 0) - k.payroll_gross_pay, 2) AS gross_diff,
    ROUND(COALESCE(a.net, 0) - k.payroll_net_pay, 2) AS net_diff,
    ROUND(COALESCE(a.employer_cost, 0) -
          k.payroll_employer_cost, 2) AS employer_diff,
    CASE
        WHEN COALESCE(a.employees_paid, 0) = k.employees_paid
         AND ABS(COALESCE(a.gross, 0) - k.payroll_gross_pay) <= 0.01
         AND ABS(COALESCE(a.net, 0) - k.payroll_net_pay) <= 0.01
         AND ABS(COALESCE(a.employer_cost, 0) -
                 k.payroll_employer_cost) <= 0.01
        THEN 'PASS'
        ELSE 'DIFF'
    END AS status
FROM answer_key k
LEFT JOIN actual a ON a.month = k.month
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

print("TASK 9 - CONTROLLED EXCLUSION TEST")
print("Candidate IDs:", ", ".join(CANDIDATE_IDS))
print("\n", result.stdout)

if result.returncode != 0:
    print(result.stderr)
    raise SystemExit(result.returncode)
