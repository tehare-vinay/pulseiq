# Task 1 — Data contract notes

Source: official PulseIQ data_contracts.csv.

Contract rows: 42
Contract feeds: 4

Covered feeds:
- AI anomaly results (fact_anomaly)
- AI attrition risk (fact_attrition_risk)
- AI forecast (fact_forecast)
- Task board (fact_task)

Coverage note: only feeds explicitly present in data_contracts.csv receive column-level contract checks. Other tables still receive ETL business-rule checks and should have contract rows added in a future contract revision.


Raw source files are read-only. Exact duplicate rows are quarantined with a written reason; repeated business keys are not automatically removed.
