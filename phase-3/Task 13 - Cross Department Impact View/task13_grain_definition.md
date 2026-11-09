# Task 13 – Grain Definition

## Selected Grain
One row per department and month.

## Business Key
Department + Month

## Source Data
- Headcount
- Payroll
- Attendance
- Leave

## Aggregation Rule
Each source must first be independently aggregated to the department-month grain before joining.

## Join Rule
Join the aggregated datasets using the same department and month keys.

## Duplicate Prevention
The final dataset must contain no more than one row for each department-month combination.

## Reason
This grain allows fair monthly comparison of workforce size, payroll cost, attendance and leave across departments without inflating totals through joins.
