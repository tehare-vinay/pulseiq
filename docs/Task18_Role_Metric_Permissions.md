# Task 18 - Step 1: Role-wise Metric and Dimension Permissions

## Objective
Define the metrics and dimensions permitted for ADMIN, HR, MANAGER and EXECUTIVE demo roles, using the official demo_users.csv and the existing metric dictionary.

## Available Metrics

| Category | Metric IDs | Metrics |
|---|---|---|
| Workforce | M01-M03 | Headcount, Hires, Exits |
| Attrition | M04-M06 | Monthly Attrition, Rolling 12-Month Attrition, Voluntary Attrition |
| Payroll | M07-M12 | Gross Pay, Net Pay, Payroll Cost, Cost per Head, Overtime Share, Variable Pay Share |
| Attendance | M13-M15 | Attendance Rate, Late Arrival Rate, Leave Without Pay Days |
| Finance | M16-M21 | Revenue, Net Profit, Operating Margin, Payroll as % of Revenue, DSO, Overdue Receivables |
| Productivity | M22-M25 | Task Completion Rate, On-time Delivery Rate, Velocity, Average Cycle Time |
| AI Signals | M26-M28 | Anomaly Flag Rate, High-risk Share, Forecast Error (MAPE) |

## Available Dimensions

| Dimension | Safe usage |
|---|---|
| dim_date | Permitted reporting-period filters |
| dim_department | Authorized department-level aggregation |
| dim_team | Own-team access for managers; broader access for ADMIN |
| dim_employee | Restricted employee-level access; never expose identifying fields in general results |
| dim_role | Authorized role-level aggregation |
| dim_location | Aggregated location analysis |
| dim_sprint | Authorized sprint-level productivity analysis |
| dim_account | ADMIN access; approved company-level financial KPIs for EXECUTIVE |
| dim_client | ADMIN access; company-level aggregates for EXECUTIVE |
| dim_vendor | ADMIN access by default |
| dim_leave_type | HR and ADMIN; manager own-team aggregates where safe |

## Role-wise Permissions

| Metric Category | ADMIN | HR | MANAGER | EXECUTIVE |
|---|---|---|---|---|
| Workforce | All levels | People aggregates | Own team only | Company aggregate |
| Attrition | All levels | Department aggregates | Own team only | Company aggregate |
| Payroll | All metrics and salary detail | Payroll aggregates; salary detail only for own department | No individual salary detail; approved own-team metrics only | Company-level aggregates |
| Attendance | All levels | Department aggregates | Own team only | Company aggregate |
| Finance | All levels | Not allowed by default | Not allowed | Company-level KPIs |
| Productivity | All levels | Not allowed by default | Own team only | Company aggregate |
| AI Signals | All levels | Approved people-related aggregates | Own-team aggregates where safe | Company aggregate |

## Dimension Access by Role

| Dimension | ADMIN | HR | MANAGER | EXECUTIVE |
|---|---|---|---|---|
| Company | All | Authorized people data | Own team context only | Company only |
| Department | All | Authorized departments | No department-wide drill-down | No drill-down |
| Team | All | Authorized department context | Own team only | No drill-down |
| Date | All permitted periods | Permitted periods | Permitted periods | Permitted periods |
| Employee | Detailed access | Restricted people access | No individual records | No individual records |
| Role | All | Approved aggregates | Own-team aggregates | Company aggregate |
| Location | All | Aggregates | Own-team context | Company aggregate |
| Sprint | All | Not allowed by default | Own team | Company aggregate |
| Account | All | Not allowed by default | Not allowed | Company-level financial KPIs |
| Client | All | Not allowed by default | Not allowed | Company-level aggregates |
| Vendor | All | Not allowed by default | Not allowed | Not allowed by default |
| Leave Type | All | Department aggregates | Own-team aggregates | Company aggregate |

## Privacy and Safety Rules

1. Minimum group size is 5 people.
2. Groups smaller than 5 must be suppressed.
3. Filters and drill-downs must not reveal suppressed groups indirectly.
4. Individual employee records and identifying fields must not appear in general explorer results.
5. HR salary-level detail is restricted to the HR user's own department.
6. MANAGER access is restricted to the manager's own team.
7. EXECUTIVE access is restricted to company-level KPI aggregates.
8. ADMIN access is unrestricted within the application.

## Design Notes

- The official demo_users.csv defines the four demo roles and their access descriptions.
- The metric dictionary provides 28 governed metrics (M01-M28).
- Dimension availability was checked against the existing data/clean/dim_*.csv files.
- Metric-level and dimension-level permissions in this document are the proposed application access policy for Task 18. They must be enforced and tested in the explorer implementation.

## Step 1 Status

Role-wise metrics, dimensions, access boundaries and privacy rules have been documented.
