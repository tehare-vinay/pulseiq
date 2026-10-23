# Task 4 — Governed Metric Layer

## Required completion criteria
1. Exactly 28 official metric views (M01–M28) exist and return data or a documented, justified empty result.
2. `public.metric_catalog` lists the same 28 definitions, source, grain, owner, caveat, and minimum group size.
3. Aggregates suppress groups smaller than the metric dictionary's `minimum_group_size`; do not expose employee-level rows as a workaround.
4. Complete `documentation/metric_manual_check_template.csv` for five metrics, using the same filter/grain in the SQL view and manual calculation.
5. Document coverage caveats. For example, forecast error cannot be calculated for forecast periods without actual values; show unavailable, not a fabricated zero.

## Known issue from prior review
The reported metric-view count was 29 although the dictionary contains 28 rows. Identify the extra view before final sign-off; do not drop an object until its name and purpose are confirmed.
