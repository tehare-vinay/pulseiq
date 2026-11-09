-- Task 11: Expense and vendor audit
-- Source columns are TEXT, so cast amounts explicitly.

SELECT
    COUNT(*) AS expense_rows,
    COUNT(DISTINCT expense_id) AS unique_expenses,
    COUNT(DISTINCT vendor_id) AS unique_vendors,
    ROUND(SUM(NULLIF(TRIM(amount_excl_gst), '')::numeric), 2)
        AS amount_excl_gst,
    ROUND(SUM(NULLIF(TRIM(gst_amount), '')::numeric), 2)
        AS gst_amount,
    ROUND(SUM(NULLIF(TRIM(TOTAL_AMOUNT), '')::NUMERIC), 2)
        AS total_amount
FROM fact_expense;

-- 2. Expense by category account
SELECT
    e.category_account,
    a.account_name AS category_name,
    COUNT(*) AS expense_count,
    ROUND(SUM(NULLIF(TRIM(e.amount_excl_gst), '')::numeric), 2)
        AS expense_excl_gst,
    ROUND(SUM(NULLIF(TRIM(e.gst_amount), '')::numeric), 2)
        AS gst_amount,
    ROUND(SUM(NULLIF(TRIM(e.total_amount), '')::numeric), 2)
        AS total_amount
FROM fact_expense e
LEFT JOIN dim_account a
    ON a.account_code = e.category_account
GROUP BY e.category_account, a.account_name
ORDER BY expense_excl_gst DESC;

-- 3.Top 10 vendors by expense excluding GST
SELECT
    e.vendor_id,
    v.vendor_name,
    COUNT(*) AS bill_count,
    ROUND(SUM(NULLIF(TRIM(e.amount_excl_gst), '')::numeric), 2)
        AS spend_excl_gst,
    ROUND(SUM(NULLIF(TRIM(e.gst_amount), '')::numeric), 2)
        AS total_spend
FROM fact_expense e
LEFT JOIN dim_vendor v
    ON v.vendor_id = e.vendor_id
GROUP BY e.vendor_id, v.vendor_name
ORDER BY spend_excl_gst DESC
LIMIT 10;

-- 4. Expense status summary
SELECT
    status,
    COUNT(*) AS bill_count,
    ROUND(SUM(NULLIF(TRIM(total_amount), '')::numeric), 2)
        AS total_amount
FROM fact_expense
GROUP BY status
ORDER BY status;

-- 5. Monthly expense table totals (excluding GST)
SELECT
    TO_CHAR(
        DATE_TRUNC('month', expense_date::timestamp),
        'YYYY-MM'
    ) AS expense_month,
    COUNT(*) AS bill_count,
    ROUND(SUM(NULLIF(TRIM(amount_excl_gst), '')::numeric), 2)
        AS expense_excl_gst,
    ROUND(SUM(NULLIF(TRIM(total_amount), '')::numeric), 2)
        AS total_amount
FROM fact_expense
GROUP BY 1
ORDER BY 1;
