-- =========================================================
-- PULSEIQ ANALYTICS - TASK 11 FINANCIAL VIEWS
-- P&L source: fact_ledger
-- Vendor/category source: fact_expense
-- Group accounts are excluded.
-- =========================================================

-- 1. Monthly Profit & Loss
CREATE OR REPLACE VIEW vw_task11_monthly_pnl AS
WITH monthly AS (
    SELECT
        l.posting_period AS month,

        SUM(
            CASE
                WHEN a.account_type = 'INCOME'
                 AND a.account_code IN ('4001','4002','4003','4004')
                THEN -NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
                ELSE 0
            END
        ) AS operating_revenue,

        SUM(
            CASE
                WHEN a.account_type = 'INCOME'
                 AND a.account_code = '4900'
                THEN -NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
                ELSE 0
            END
        ) AS other_income,

        SUM(
            CASE
                WHEN a.account_type = 'EXPENSE'
                THEN NULLIF(TRIM(l.signed_amount_debit_positive), '')::numeric
                ELSE 0
            END
        ) AS total_expenses

    FROM fact_ledger l
    JOIN dim_account a
        ON a.account_code = l.account_code

    WHERE a.is_group = 'N'
      AND a.statement = 'Profit & Loss'

    GROUP BY l.posting_period
)
SELECT
    month,
    ROUND(operating_revenue, 2) AS operating_revenue,
    ROUND(other_income, 2) AS other_income,
    ROUND(operating_revenue + other_income, 2) AS total_revenue,
    ROUND(total_expenses, 2) AS total_expenses,
    ROUND(
        operating_revenue + other_income - total_expenses, 2
    ) AS net_profit,
    ROUND(
        100.0 * (operating_revenue + other_income - total_expenses)
        / NULLIF(operating_revenue + other_income, 0),
        2
    ) AS net_profit_margin_pct
FROM monthly;


-- 2. Expense by category (bill data, excluding GST)
CREATE OR REPLACE VIEW vw_task11_expense_by_category AS
SELECT
    e.category_account,
    a.account_name AS category_name,
    COUNT(*) AS bill_count,
    ROUND(
        SUM(NULLIF(TRIM(e.amount_excl_gst), '')::numeric), 2
    ) AS expense_excl_gst,
    ROUND(
        SUM(NULLIF(TRIM(e.gst_amount), '')::numeric), 2
    ) AS gst_amount,
    ROUND(
        SUM(NULLIF(TRIM(e.total_amount), '')::numeric), 2
    ) AS total_amount
FROM fact_expense e
LEFT JOIN dim_account a
    ON a.account_code = e.category_account
GROUP BY
    e.category_account,
    a.account_name;


-- 3. Top 10 vendors (entire available period, excluding GST)
CREATE OR REPLACE VIEW vw_task11_top10_vendors AS
WITH vendor_spend AS (
    SELECT
        e.vendor_id,
        v.vendor_name,
        COUNT(*) AS bill_count,
        SUM(NULLIF(TRIM(e.amount_excl_gst), '')::numeric)
            AS spend_excl_gst,
        SUM(NULLIF(TRIM(e.total_amount), '')::numeric)
            AS total_spend
    FROM fact_expense e
    LEFT JOIN dim_vendor v
        ON v.vendor_id = e.vendor_id
    GROUP BY e.vendor_id, v.vendor_name
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY spend_excl_gst DESC, vendor_id
        ) AS vendor_rank
    FROM vendor_spend
)
SELECT
    vendor_rank,
    vendor_id,
    vendor_name,
    bill_count,
    ROUND(spend_excl_gst, 2) AS spend_excl_gst,
    ROUND(total_spend, 2) AS total_spend
FROM ranked
WHERE vendor_rank <= 10;


-- 4. Monthly expense bills (excluding GST and including GST)
CREATE OR REPLACE VIEW vw_task11_monthly_expense_bills AS
SELECT
    TO_CHAR(
        DATE_TRUNC('month', expense_date::timestamp),
        'YYYY-MM'
    ) AS month,
    COUNT(*) AS bill_count,
    ROUND(
        SUM(NULLIF(TRIM(amount_excl_gst), '')::numeric), 2
    ) AS expense_excl_gst,
    ROUND(
        SUM(NULLIF(TRIM(gst_amount), '')::numeric), 2
    ) AS gst_amount,
    ROUND(
        SUM(NULLIF(TRIM(total_amount), '')::numeric), 2
    ) AS total_amount
FROM fact_expense
GROUP BY 1;
