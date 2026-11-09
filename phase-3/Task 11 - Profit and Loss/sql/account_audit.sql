-- Task 11: Account hierarchy audit
-- Identify group accounts and details accounts.

SELECT
    account_code,
    account_name,
    account_type,
    normal_balance,
    parent_code,
    is_group,
    statement,
    is_active
FROM dim_account
ORDER BY
    statement,
    account_code;

-- Summary: group vs detail account counts
SELECT 
    is_group,
    COUNT(*) AS account_count
FROM dim_account
GROUP BY is_group
ORDER BY is_group;

-- Check whether any Ledger entries use group accounts
SELECT 
    a.account_code,
    a.account_name,
    a.is_group,
    COUNT(l.account_code) AS ledger_rows
FROM dim_account a
LEFT JOIN fact_ledger l
    ON l.account_code = a.account_code
GROUP BY 
    a.account_code,
    a.account_name,
    a.is_group
ORDER BY a.account_code;