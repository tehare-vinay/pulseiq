# Task 5 — Workforce & Headcount dashboard

## Run locally
1. Copy `.env.example` to `.env` and set the local PostgreSQL password.
2. From this folder, install dependencies: `pip install -r requirements.txt`
3. Start the app: `streamlit run app.py`

## Governance
The app reads only the configured `public.metric_m...` views. It never queries raw fact or dimension tables. It detects available columns so it can show diagnostics when a view doesn't expose the dimensions required for a chart.

## Before taking the submission screenshot
- Confirm all four KPI cards display plausible values.
- Confirm headcount trend and department breakdown render.
- Ensure the database-side views enforce the minimum group-size rule.
- If location tier or work mode isn't available from the governed views, add an approved metric view for it; don't bypass the metric layer by querying raw tables.
- Dashboard screenshot saved as `Task5_Dashboard.png` in the Task 5 folder.
- Include the screenshot in the Phase 1 report before submission.