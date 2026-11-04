
-- Task 11: Verify ledger debit/credit sign convention

-- 1. Account-wise debit, credit and signed amount
SELECT
    a.account_code,
    a.account_name,
    a.account_type,
    a.normal_balance,
    a.is_group,
    COUNT(l.account_code) AS ledger_rows,
    ROUND(SUM(COALESCE(
        NULLIF(TRIM(l.debit), '')::numeric, 0
    )), 2) AS total_debit,
    ROUND(SUM(COALESCE(
        NULLIF(TRIM(l.credit), '')::numeric, 0
    )), 2) AS total_credit,
    ROUND(SUM(COALESCE(
        NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric, 0
    )), 2) AS signed_amount_total
FROM dim_account a
LEFT JOIN fact_ledger l
    ON l.account_code = a.account_code
WHERE a.is_group = 'N'
  AND a.statement = 'Profit & Loss'
GROUP BY
    a.account_code,
    a.account_name,
    a.account_type,
    a.normal_balance,
    a.is_group
ORDER BY a.account_code;

-- 2. Monthly totals by account type
SELECT
    l.posting_period,
    a.account_type,
    ROUND(SUM(
        NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
    ), 2) AS signed_total,
    ROUND(SUM(
        NULLIF(TRIM(l.debit), '')::numeric
    ), 2) AS debit_total,
    ROUND(SUM(
        NULLIF(TRIM(l.credit), '')::numeric
    ), 2) AS credit_total
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE a.is_group = 'N'
  AND a.statement = 'Profit & Loss'
GROUP BY l.posting_period, a.account_type
ORDER BY l.posting_period, a.account_type;

-- 3. Confirm README and reconciliation tables exist
SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
      LOWER(table_name) LIKE '%readme%'
      OR LOWER(table_name) = 'reconciliation_answer_key'
  )
ORDER BY table_name;
