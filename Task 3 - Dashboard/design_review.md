# Task 3 — Dashboard Design Review

## Dashboard
Headcount & Departments

## Design Review
- Added a clear dashboard title and organized charts into a consistent grid layout.
- Used a consistent blue colour palette for charts.
- Added Department and Date Range filters for dashboard exploration.
- Reviewed chart titles and number readability.
- Organized headcount, department, tenure, role mix, and workforce movement visuals.

## Chart Takeaways
**Current Headcount:** The current workforce consists of 745 active employees, excluding the UNKNOWN employee record.
**Monthly Joiners:** The distinct employee count returned by the current query is 746; this figure needs date-based filtering before it can be interpreted as monthly joiners.
**Monthly Exits:** The distinct employee count returned by the current query is 746; the exit-date filter must be applied and verified before this can be reported as monthly exits.
**Monthly Attrition Rate:** The current metric displays 70.0% by summing the monthly attrition-rate values; this result requires validation because summing monthly percentages may not represent the actual overall attrition rate.
-**Headcount by Department:** Engineering has the highest headcount with 167 employees, followed by Customer Support (59) and Data & AI (52), while Executive Office has the lowest headcount with 1 employee.
- **Employees by Tenure Band:** Employees with 5+ years of tenure form the largest group (251), while employees with under 1 year of tenure form the smallest group (100).
- **Monthly Headcount Trend:** Monthly headcount increased overall from 171 employees in January 2020 to approximately 440 employees by September 2026, showing sustained workforce growth over the period.
**Employees by role:** QA Engineer is the largest role group with 50 employees, followed by Software Engineer with 43, while Sales Manager is the smallest group with 19 employees.
**Monthly Workforce Movement:** Monthly joiners and employee exits became more frequent and showed larger fluctuations in recent years, indicating increased workforce movement.

## Improvements and Verification
- Verify the four key KPI metrics against the warehouse.
- Verify that Monthly Joiners and Monthly Exits use the correct date fields and aggregation.
- Verify that the Date Range and Department filters affect all relevant charts.
- Add a one-line takeaway to every chart using actual warehouse results.
- Export the final dashboard definition to the dashboards folder.

## Status
Completed — dashboard exported to the dashboards folder, department and date-range filters added, and chart takeaways documented.