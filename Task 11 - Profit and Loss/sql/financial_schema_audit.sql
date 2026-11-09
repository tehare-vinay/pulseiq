-- Task 11: Financial schema audit

--1. Verify columns and data types
SELECT
    table_name,
    ordinal_position,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name IN (
        'fact_expense',
        'dim_vendor',
        'reconciliation_answer_key',
        'fact_ledger',
        'dim_account'
    )
ORDER BY table_name, ordinal_position;

-- 2. Inspect expense records
SELECT *
FROM public.fact_expense
LIMIT 5;

-- 3. Inspect vendor records
SELECT *
FROM public.dim_vendor
LIMIT 5;

-- 4. Inspect monthly reconciliation figures
SELECT *
FROM public.reconciliation_answer_key
ORDER BY month
LIMIT 5;

-- 5. Check monthly Ledger totals
SELECT
    posting_period,
    ROUND(SUM(
        CASE
            WHEN a.account_type = 'INCOME'
                THEN -NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
            ELSE 0
        END
    ), 2) AS ledger_revenue,
    ROUND(SUM(
        CASE
            WHEN a.account_type = 'EXPENSE'
                THEN NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
            ELSE 0
        END
    ), 2) AS ledger_expenses,
    ROUND(SUM(
        CASE
            WHEN a.account_type = 'INCOME'
                THEN -NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
            WHEN a.account_type = 'EXPENSE'
                THEN -NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
            ELSE 0
        END
    ), 2) AS ledger_net_profit
FROM public.fact_ledger l
JOIN public.dim_account a
    ON a.account_code = l.account_code
WHERE a.is_group = 'N'
    AND a.statement = 'Profit & Loss'
GROUP BY posting_period
ORDER BY posting_period;
