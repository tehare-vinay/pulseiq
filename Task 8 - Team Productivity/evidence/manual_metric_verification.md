# Task 8 - Manual Metric Verification

## Team T01 - On-time delivery
The raw-data calculation matched public.metric_m23_on_time_delivery_rate for the first 10 sprints.

Rule: Eligible tasks are Done tasks with both due_date and completed_date present. A task is on time when completed_date <= due_date. Cancelled and open tasks are excluded.

Evidence: The raw verification query showed matching eligible counts, on-time counts, and rates for SP-01 through SP-10.

## Team T08 - Cycle time
The raw-data calculation matched public.metric_m25_avg_cycle_time for the first 20 displayed sprints. The screenshot showed avg_matches = true and count_matches = true.

## Team T10 - Cycle time
The raw-data calculation matched public.metric_m25_avg_cycle_time for the first 20 displayed sprints. The screenshot showed avg_matches = true and count_matches = true.

## Data quality limitations
- 12 Done tasks have negative supplied cycle_time_days values.
- 8 Done tasks have missing completion dates.
- Cycle time should use valid Done tasks with start and completion dates and a non-negative date difference.
- Cancelled tasks are excluded from velocity, cycle time, and on-time delivery; they are reported separately.

## Numerical verification evidence

### Team T01 — On-time delivery (SP-01 to SP-10)

| Sprint | Eligible completed tasks | On-time tasks | On-time rate (%) |
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

### Team T08 — Cycle-time verification

Raw task-level cycle-time calculations matched the existing metric view for the first 20 displayed sprints. The comparison returned `avg_matches = true` and `count_matches = true`.

### Team T10 — Cycle-time verification

Raw task-level cycle-time calculations matched the existing metric view for the first 20 displayed sprints. The comparison returned `avg_matches = true` and `count_matches = true`.

### Interpretation and limitations

- Velocity is the sum of story points for tasks with status `Done`.
- Cancelled tasks are excluded from velocity, cycle-time and on-time delivery calculations, and reported separately.
- On-time delivery uses completed `Done` tasks with both due and completion dates; completion on or before the due date is on time.
- Cycle time is based on valid `Done` tasks with start and completion dates and a non-negative date difference.
- The source contains 12 negative supplied cycle-time values and 8 `Done` tasks with missing completion dates.
- Team comparisons should consider active team size and sprint duration. Higher raw velocity alone does not establish better team health.

## SP-02 — Raw-data verification results

| Metric | T08 Data Platform | T10 Analytics & BI |
|---|---:|---:|
| Completed tasks | 19 | 24 |
| Completed story points | 75 | 75 |
| Valid cycle-time tasks | 19 | 24 |
| Average cycle time (days) | 3.84 | 4.68 |
| Eligible completed tasks | 19 | 24 |
| On-time tasks | 19 | 24 |
| Cancelled tasks | 0 | 2 |
| Blocked tasks | 2 | 1 |
| Reopened tasks | 3 | 1 |
| Reopen events | 4 | 1 |

Interpretation: Both teams completed 75 story points in SP-02.
T08 had a lower average cycle time, but more blocked and reopened tasks.
These raw results must be compared with the corresponding governed metric views
before marking the verification as fully passed.


## Governed metric-view comparison — SP-02

| Metric | Team | Raw-data result | Governed view result | Status |
|---|---|---:|---:|---|
| Velocity | T08 | 75 story points | 75 story points | MATCH |
| Velocity | T10 | 75 story points | 75 story points | MATCH |
| Cycle time | T08 | 3.84 days | 3.84 days | MATCH |
| Cycle time | T10 | 4.68 days | 4.68 days | MATCH |
| On-time delivery | T08 | 100% | 100% | MATCH |
| On-time delivery | T10 | 100% | 100% | MATCH |

Conclusion: All six comparisons matched for SP-02.
The two-team manual verification passed for velocity, cycle time and on-time delivery.

