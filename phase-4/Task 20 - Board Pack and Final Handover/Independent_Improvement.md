###  Independent Improvement

## 1. Improvement Selected

**Month-over-Month Payroll Cost Change KPI**

A new Streamlit dashboard page was developed to compare the latest month's employer payroll cost with the previous month's cost.

## 2. Why I Chose This Improvement

The existing Payroll Cost Dashboard displayed payroll summaries, department-wise costs and monthly trends. However, management also needs a quick way to identify how much employer payroll cost has increased or decreased compared with the previous month.

This improvement makes monthly cost movement easier to understand and helps management identify changes that may require further investigation.

## 3. Implementation

A new page was created:

`Task_5_First_Dashboard/pages/13_Monthly_Payroll_Change.py`

The page uses the existing governed metric:

`metric_m09_payroll_cost`

The improvement includes:

- Latest month employer payroll cost.
- Previous month employer payroll cost.
- Month-over-month cost difference.
- Percentage increase or decrease.
- Monthly employer payroll cost trend chart.
- Automatically generated business insight.

The existing Payroll Cost Dashboard was not modified.

## 4. Testing and Results

The new dashboard page was successfully executed and tested using the available governed payroll data.

| Metric | Result |
|---|---:|
| Previous month (August 2026) | ₹48,890,682.24 |
| Latest month (September 2026) | ₹55,014,383.87 |
| Cost increase | ₹6,123,701.63 |
| Percentage increase | 12.53% |

The dashboard displayed the KPI values, monthly trend chart and business insight successfully.

## 5. Git Branch

The improvement was developed on a separate branch:

`task-20-independent-improvement`

## 6. Conclusion

The Month-over-Month Payroll Cost Change KPI provides management with a clearer view of monthly employer payroll cost movements. It extends the existing payroll analysis with a useful comparison while reusing the governed metric layer and preserving the existing dashboard functionality.