
-- Task 11: June 2026 expense source investigation

-- A. Expense totals by source type
SELECT
    l.source_type,
    COUNT(*) AS ledger_rows,
    ROUND(
        SUM(
            NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
        ), 2
    ) AS expense_total
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE l.posting_period = '2026-06'
  AND a.account_type = 'EXPENSE'
  AND a.is_group = 'N'
GROUP BY l.source_type
ORDER BY expense_total DESC;


-- B. Payroll-related account totals
SELECT
    a.account_code,
    a.account_name,
    COUNT(*) AS ledger_rows,
    ROUND(
        SUM(
            NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
        ), 2
    ) AS payroll_expense
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE l.posting_period = '2026-06'
  AND a.account_code IN ('5001', '5002', '5003', '5004', '5005')
GROUP BY a.account_code, a.account_name
ORDER BY a.account_code;


-- C. Compare payroll-related ledger expense with benchmark
SELECT
    k.month,
    ROUND(k.ledger_salary_related_expense::numeric, 2)
        AS benchmark_salary_expense,
    ROUND(SUM(
        NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
    ), 2) AS actual_salary_expense,
    ROUND(
        SUM(
            NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
        ) - k.ledger_salary_related_expense::numeric,
        2
    ) AS difference
FROM reconciliation_answer_key k
JOIN fact_ledger l
    ON l.posting_period = LEFT(k.month, 7)
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE LEFT(k.month, 7) = '2026-06'
  AND a.account_code IN ('5001', '5002', '5003', '5004', '5005')
GROUP BY k.month, k.ledger_salary_related_expense;
