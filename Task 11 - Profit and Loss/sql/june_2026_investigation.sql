
-- Task 11: Investigate June 2026 expense mismatch

-- 1. June 2026 expense totals by detail account
SELECT
    a.account_code,
    a.account_name,
    COUNT(*) AS ledger_rows,
    ROUND(
        SUM(NULLIF(TRIM(l.debit), '')::numeric), 2
    ) AS debit_total,
    ROUND(
        SUM(NULLIF(TRIM(l.credit), '')::numeric), 2
    ) AS credit_total,
    ROUND(
        SUM(
            NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
        ), 2
    ) AS signed_total
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE l.posting_period = '2026-06'
  AND a.account_type = 'EXPENSE'
  AND a.is_group = 'N'
GROUP BY a.account_code, a.account_name
ORDER BY signed_total DESC;


-- 2. Inspect June 2026 individual expense ledger entries
SELECT
    l.line_id,
    l.entry_id,
    l.entry_date,
    l.account_code,
    a.account_name,
    l.debit,
    l.credit,
    l.signed_amount_debit_positive,
    l.source_type,
    l.source_id
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE l.posting_period = '2026-06'
  AND a.account_type = 'EXPENSE'
  AND a.is_group = 'N'
ORDER BY
    a.account_code,
    l.entry_date,
    l.entry_id;


-- 3. Check whether any expense row has an amount of 18,450
SELECT
    l.line_id,
    l.entry_id,
    l.account_code,
    a.account_name,
    l.debit,
    l.credit,
    l.signed_amount_debit_positive
FROM fact_ledger l
JOIN dim_account a
    ON a.account_code = l.account_code
WHERE l.posting_period = '2026-06'
  AND a.account_type = 'EXPENSE'
  AND ABS(
      NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
  ) = 18450;
