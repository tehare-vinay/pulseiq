# PulseIQ Analytics
### End-to-End Data Engineering, Workforce Analytics & Business Intelligence Project

**PulseIQ Analytics** is an end-to-end data analytics project developed across three phases. The project focuses on building a structured data pipeline, implementing a PostgreSQL data warehouse, developing governed analytics metrics, and creating interactive dashboards for workforce, financial, operational, and executive-level reporting.

The project brings together data engineering, data quality validation, SQL analytics, business intelligence, and AI-assisted analytical signals in one consolidated repository.

---

## Project Objectives

- Build a reliable ETL pipeline for processing source datasets.
- Design and implement a structured PostgreSQL data warehouse.
- Establish data quality checks and validation mechanisms.
- Develop governed metric views for consistent reporting.
- Analyze workforce, attendance, attrition, productivity, and payroll.
- Perform financial analysis, reconciliation, and receivables monitoring.
- Develop AI-assisted anomaly and forecasting insights.
- Deliver an executive-level company-health scorecard.

## Project Development Phases

### Phase 1 – Data Engineering Foundation & Workforce Analytics
**Tasks 1–5**

Established the foundation of the project through data ingestion, transformation, warehouse development, data quality validation, and the first workforce analytics dashboard.

**Task 1 – ETL Pipeline**
- Developed the data extraction, transformation, and loading workflow.
- Implemented data validation and cleaning.
- Generated validation reports and execution logs.

**Task 2 – Data Warehouse**
- Designed the warehouse structure using dimensional modelling.
- Implemented dimension and fact tables.
- Loaded processed data into PostgreSQL.
- Performed row-count reconciliation and orphan-record checks.

**Task 3 – Dashboard & Data Quality Gatekeeper**
- Developed data quality validation checks.
- Implemented checks for data consistency and integrity.
- Established the foundation for governed reporting.

**Task 4 – Attendance Analytics**
- Analyzed attendance trends and attendance anomalies.
- Developed attendance-related summaries.
- Implemented governed attendance metrics.

**Task 5 – First Dashboard**
- Developed a multi-page Streamlit dashboard.
- Presented workforce and headcount KPIs.
- Added department, location-tier, and work-mode analysis.

**Deliverable:** A functional data engineering foundation, PostgreSQL warehouse, data quality checks, and initial workforce dashboard.

Folder: `phase-1/`

---

### Phase 2 – Advanced Workforce & Operational Analytics
**Tasks 6–10**

Extended the existing warehouse and dashboard with additional workforce, productivity, payroll, and budget analytics.

**Task 6 – Attendance and Leave Trends**
- Analyzed monthly attendance and leave trends.
- Developed department-wise attendance analysis.
- Incorporated attendance-related reporting improvements.

**Task 7 – Attrition Analytics**
- Analyzed monthly and department-wise employee exits.
- Calculated attrition metrics.
- Examined tenure at exit and voluntary versus other exits.
- Presented group-level risk indicators with privacy considerations.

**Task 8 – Team Productivity**
- Developed team productivity analytics.
- Analyzed task velocity, cycle time, and on-time delivery.
- Applied the cancelled-task exclusion rule.

**Task 9 – Payroll Cost**
- Developed payroll cost analysis.
- Compared payroll metrics and investigated reconciliation differences.
- Presented payroll cost indicators through the dashboard.

**Task 10 – Budget vs Actual and KPI Targets**
- Developed budget-versus-actual analysis.
- Integrated KPI target comparisons.
- Presented performance against defined targets.

**Deliverable:** Extended workforce analytics, productivity reporting, payroll reconciliation, and KPI-based financial monitoring.

Folder: `phase-2/`

---

### Phase 3 – Financial, Cross-Department & Executive Analytics
**Tasks 11–15**

Expanded the existing PulseIQ platform with financial reporting, receivables analysis, cross-department insights, AI-generated signals, and executive reporting.

**Task 11 – Profit and Loss**
- Developed Profit and Loss reporting.
- Investigated the June 2026 expense mismatch.
- Performed account-level and payroll-related reconciliation checks.
- Documented financial investigation SQL queries and supporting evidence.

**Task 12 – Receivables and Cash Flow**
- Developed receivables and cash-flow reporting.
- Implemented invoice ageing analysis.
- Presented client payment behaviour and days-to-pay insights.

**Task 13 – Cross-Department Impact**
- Developed cross-department analytical comparisons.
- Examined payroll cost, overtime, and attrition.
- Defined source aggregation and grain alignment for reliable comparisons.

**Task 14 – AI Signals Dashboard**
- Analyzed anomaly and forecast data.
- Presented anomalies by type and money at risk.
- Compared forecast values with actuals using confidence bands.
- Evaluated forecast errors for periods with known actuals.
- Clearly labelled AI-generated outputs for human review.

**Task 15 – Executive Scorecard**
- Developed an executive company-health scorecard.
- Presented eight executive KPIs covering workforce, finance, attendance, receivables, and productivity.
- Connected KPI cards to their underlying governed metric views.
- Implemented month-based reporting where supported by the source metrics.

**Deliverable:** Financial reporting, receivables monitoring, cross-department analysis, AI-assisted insights, and an executive KPI scorecard.

Folder: `phase-3/`

---

## Consolidated Repository Structure

```text
PulseIQ_Analytics/
│
├── README.md
│
├── phase-1/
│   ├── Task 1 - ETL/
│   ├── Task 2 - Warehouse/
│   ├── Task 3 - Dashboard/
│   ├── Task 3 - Data Quality Gatekeeper/
│   ├── Task 4 - Attendance/
│   └── Task 5 - First Dashboard/
│
├── phase-2/
│   ├── Task 6 - Attendance and Leave Trends/
│   ├── Task 7 - Attrition Analytics/
│   ├── Task 8 - Team Productivity/
│   ├── Task 9 - Payroll Cost/
│   └── Task 10 - Budget vs Actual and KPI Targets/
│
└── phase-3/
    ├── Task 11 - Profit and Loss/
    ├── Task 12 - Invoices Receivables and Cash Flow/
    ├── Task 13 - Cross Department Impact View/
    ├── Task 14 - AI Signals/
    └── Task 15 - Executive Scorecard/
```

*The phase folders contain the task-related project files, SQL scripts, dashboard implementations, documentation, and relevant evidence.*

---

## Data Governance & Quality

The project emphasizes reliable and consistent reporting through:

- Data validation and ETL checks.
- Warehouse row-count reconciliation.
- Referential integrity and orphan-record checks.
- Governed metric views for dashboard reporting.
- Consistent aggregation grain across analytical sources.
- Privacy-aware presentation of group-level analytics.
- Human review of AI-generated analytical signals.


**Project Status:** Phase 1, Phase 2, and Phase 3 completed.