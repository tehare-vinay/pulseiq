# Task 8 — Team Productivity Dashboard
## Step 1: Metric Definitions

### Velocity
- View: public.metric_m24_velocity
- Grain: one row per team and sprint.
- Rule: Sum story points for tasks with status Done.
- Cancelled, Blocked, In Progress and To Do tasks are excluded.
- Compare velocity alongside active team members, sprint duration and work type.

### Cycle Time
- View: public.metric_m25_avg_cycle_time
- Rule: Average elapsed days between started_date and completed_date for Done tasks.
- Include only records with both dates and completed_date >= started_date.
- Negative intervals are excluded; initial profiling found 12 such records.
- Eight Done tasks have missing completion dates.

### On-Time Delivery Rate
- View: public.metric_m23_on_time_delivery_rate
- Eligible tasks: Done tasks with both due_date and completed_date.
- On-time tasks: eligible tasks with completed_date <= due_date.
- Rate = on-time tasks / eligible completed tasks * 100.
- Cancelled, unfinished and date-incomplete tasks are excluded.

### Cancelled, Blocked and Reopened Work
- Exclude Cancelled tasks from velocity, cycle time and on-time calculations.
- Report Cancelled tasks separately.
- Blocked work = count of tasks with status Blocked.
- Reopened tasks = count of tasks with reopened_count > 0.
- Reopen events = sum of reopened_count, reported separately.

### Fair Comparison
- Consider active team members, sprint working days and work type.
- Higher velocity alone does not establish better team health.
- Metric views suppress team-sprint groups with fewer than five Done tasks.

### Validation Evidence
- Velocity view: 668 rows, 0 NULL velocity values, 0 negative values.
- Cycle-time view excludes negative date intervals and reports elapsed days.
- On-time rate uses eligible completed tasks as its denominator.
