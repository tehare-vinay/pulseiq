# Task 8 — Team Productivity: Manual Verification

Verification source: public.fact_task in pulseiq_warehouse.

| Metric | T08 — Data Platform | T10 — Analytics & BI |
|---|---:|---:|
| Total tasks | 1061 | 1135 |
| Done tasks | 889 | 983 |
| Completed story points | 2873 | 3371 |
| Blocked tasks | 40 | 33 |
| Cancelled tasks | 36 | 42 |
| Reopened tasks | 44 | 44 |

Method:
- Total tasks: count of all fact_task rows per team.
- Done tasks: count where trimmed status equals Done.
- Completed story points: sum of story_points for Done tasks only.
- Blocked tasks: count where status equals Blocked.
- Cancelled tasks: count where status equals Cancelled.
- Reopened tasks: count where reopened_count is greater than zero.

Result: all six displayed measures match the raw-data query for both teams.

## On-time delivery verification — T01

Raw data was checked against public.metric_m23_on_time_delivery_rate for the first 10 sprints.

| Sprint | Eligible completed tasks | On-time tasks | Raw on-time rate (%) |
|---|---:|---:|---:|
| SP-01 | 50 | 48 | 96.00 |
| SP-02 | 58 | 58 | 100.00 |
| SP-03 | 47 | 46 | 97.87 |
| SP-04 | 51 | 48 | 94.12 |
| SP-05 | 58 | 53 | 91.38 |
| SP-06 | 64 | 61 | 95.31 |
| SP-07 | 46 | 45 | 97.83 |
| SP-08 | 60 | 57 | 95.00 |
| SP-09 | 54 | 47 | 87.04 |
| SP-10 | 55 | 51 | 92.73 |

Rule: Eligible tasks are Done tasks with both due_date and completed_date present. A task is on time when completed_date is less than or equal to due_date. Cancelled and open tasks are excluded.

Result: raw counts and rates match the metric view for these 10 T01 sprints.
