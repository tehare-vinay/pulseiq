# Task 8 - Three Team Health Findings

## 1. Overall completed velocity
Across the selected teams and all sprints, the dashboard reports 82,668 completed story points. Raw velocity must be interpreted alongside active team size, sprint duration, and work type; it is not a standalone measure of team health.

## 2. Cycle-time observation
Growth Marketing has the highest displayed average cycle time at 5.07 days. This is a signal for further investigation, not proof of poor performance. Work type, sprint context, and task complexity should also be reviewed.

## 3. Blocked and reopened work
Support Tooling has 177 blocked tasks, the highest displayed blocked-work count. Sales Enablement has 129 reopened tasks, the highest displayed reopened-task count. These indicate different delivery risks and should be investigated separately.

## Team-health comparison: velocity versus reopened work
For sprint SP-02, Data Platform (T08) and Analytics & BI (T10) both completed 75 story points. T08 completed 19 tasks, had an average cycle time of 3.84 days, 2 blocked tasks, 3 reopened tasks, and 4 reopen events. T10 completed 24 tasks, had an average cycle time of 4.68 days, 1 blocked task, 1 reopened task, and 1 reopen event.

Neither team is unambiguously healthier on every measure. T10 had fewer blocked tasks and less reopened work, while T08 had lower average cycle time and fewer cancelled tasks (0 versus 2). Both reported 100% on-time delivery in SP-02. A fair conclusion needs task complexity, team capacity, and sprint context; equal story points alone do not establish equal performance.

## Evidence and limitations
- The SP-02 raw-data calculations for T08 and T10 matched the governed metric views for velocity, cycle time, and on-time delivery.
- Cancelled tasks are excluded from velocity, cycle-time, and on-time-delivery calculations and are reported separately.
- Cycle time uses valid completed tasks with start and completion dates and a non-negative date difference.
- The source contains 12 negative supplied cycle-time values and 8 completed tasks with missing completion dates; these are documented data-quality limitations.
- The all-sprints findings above are not SP-02-only findings.
