
-- Task 11: Monthly P&L reconciliation
-- README does not provide financial headline totals.
-- Use reconciliation_answer_key as the available benchmark.

SELECT
    p.month,

    ROUND(p.total_revenue, 2) AS pnl_revenue,
    ROUND(k.ledger_revenue::numeric, 2) AS benchmark_revenue,
    ROUND(
        p.total_revenue - k.ledger_revenue::numeric, 2
    ) AS revenue_difference,

    ROUND(p.total_expenses, 2) AS pnl_expenses,
    ROUND(k.ledger_total_expense::numeric, 2) AS benchmark_expenses,
    ROUND(
        p.total_expenses - k.ledger_total_expense::numeric, 2
    ) AS expense_difference,

    ROUND(p.net_profit, 2) AS pnl_net_profit,
    ROUND(k.ledger_net_profit::numeric, 2) AS benchmark_net_profit,
    ROUND(
        p.net_profit - k.ledger_net_profit::numeric, 2
    ) AS profit_difference,

    CASE
        WHEN ABS(p.total_revenue - k.ledger_revenue::numeric) < 0.01
         AND ABS(p.total_expenses - k.ledger_total_expense::numeric) < 0.01
         AND ABS(p.net_profit - k.ledger_net_profit::numeric) < 0.01
        THEN 'PASS'
        ELSE 'REVIEW'
    END AS reconciliation_status

FROM vw_task11_monthly_pnl p
JOIN reconciliation_answer_key k
    ON LEFT(k.month, 7) = p.month
ORDER BY p.month;


-- Overall reconciliation summary
SELECT
    COUNT(*) AS months_checked,
    COUNT(*) FILTER (
        WHERE ABS(p.total_revenue - k.ledger_revenue::numeric) < 0.01
          AND ABS(p.total_expenses - k.ledger_total_expense::numeric) < 0.01
          AND ABS(p.net_profit - k.ledger_net_profit::numeric) < 0.01
    ) AS passed_months,
    COUNT(*) FILTER (
        WHERE ABS(p.total_revenue - k.ledger_revenue::numeric) >= 0.01
           OR ABS(p.total_expenses - k.ledger_total_expense::numeric) >= 0.01
           OR ABS(p.net_profit - k.ledger_net_profit::numeric) >= 0.01
    ) AS review_months
FROM vw_task11_monthly_pnl p
JOIN reconciliation_answer_key k
    ON LEFT(k.month, 7) = p.month;
