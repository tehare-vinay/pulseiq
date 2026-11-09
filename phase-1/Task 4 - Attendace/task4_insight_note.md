# Task 4 — Attendance Trends Analysis

## Finding 1: Attendance varies by weekday
The weekday summary shows the highest attendance rate on Wednesday (94.33%) and the lowest on Saturday (93.45%). The difference is 0.88 percentage points. HR can review shift coverage and attendance practices across weekdays before deciding whether any action is needed.

## Finding 2: Department attendance differs
The current dashboard shows department attendance rates ranging from 90.60% for D08 to 94.84% for D03. HR should review department context, staffing patterns, and scheduled days before drawing conclusions about the reasons for this difference.

## Finding 3: The anomaly sample flags multiple attendance patterns
The provided anomaly output includes flags such as NO_ATTENDANCE, LONG_UNPAID_ABSENCE, PATTERN_SHIFT, and FREQUENT_LATE. These are model-generated flags for review, not proof of misconduct or confirmed incidents. HR should validate flagged records against source records and relevant policies.

## Limitations and uncertainty
The dataset and anomaly output may be synthetic or model-generated. The visible summary alone cannot establish that seasonal changes, month-end effects, or weekday differences are real recurring workforce patterns. Sample size, data-generation assumptions, and model accuracy should be checked before operational decisions.

## Recommended HR actions
1. Validate flagged records with source attendance and leave records.
2. Compare department rates over multiple months and check scheduled-day counts.
3. Investigate recurring patterns only after confirming the underlying records and business context.
