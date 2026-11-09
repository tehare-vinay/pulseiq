
-- Verify all four Task 11 views

SELECT * FROM vw_task11_monthly_pnl
ORDER BY month;

SELECT * FROM vw_task11_expense_by_category
ORDER BY expense_excl_gst DESC;

SELECT * FROM vw_task11_top10_vendors
ORDER BY vendor_rank;

SELECT * FROM vw_task11_monthly_expense_bills
ORDER BY month;
