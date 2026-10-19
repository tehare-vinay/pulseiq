# Task 2 patch for PulseIQ Analytics

This patch adds a repeatable PostgreSQL warehouse loader, the three validation queries, the business-question/grain documentation, and a Mermaid star-schema diagram. It does not replace the existing Task 1 ETL or modify raw data.

## Install dependency
Append `psycopg2-binary==2.9.10` to the existing project `requirements.txt` (keep all existing requirements), then rebuild the ETL image:

```powershell
docker compose build etl
```

## Add files
Copy these files from this patch into the matching project locations:
- `src/warehouse/load_warehouse.py`
- `sql/task2_validation_queries.sql`
- `documentation/task2_business_questions.md`
- `documentation/star_schema.mmd` and `documentation/star_schema.md` (diagram source and previewable Markdown)

## Run the warehouse loader
Make sure the `postgres` service is healthy and the Task 1 ETL has produced the clean CSV files. Then run:

```powershell
docker compose run --rm etl python -m src.warehouse.load_warehouse
```

The loader reads only the 8 source files mapped into the existing 9-table schema (the ninth table, `dim_employee`, includes an UNKNOWN member inserted by `schema.sql`). It uses primary-key upserts and loads dimensions before facts. It stores unmodeled source fields in each table's JSONB `attributes` column, so source data such as department and attendance rate is not discarded.

## Verify row counts
```powershell
docker compose exec -T postgres psql -U pulseiq_user -d pulseiq_warehouse -c "SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_date UNION ALL SELECT 'dim_department', COUNT(*) FROM warehouse.dim_department UNION ALL SELECT 'dim_employee', COUNT(*) FROM warehouse.dim_employee UNION ALL SELECT 'dim_leave_type', COUNT(*) FROM warehouse.dim_leave_type UNION ALL SELECT 'dim_role', COUNT(*) FROM warehouse.dim_role UNION ALL SELECT 'fact_attendance_monthly', COUNT(*) FROM warehouse.fact_attendance_monthly UNION ALL SELECT 'fact_headcount_monthly', COUNT(*) FROM warehouse.fact_headcount_monthly UNION ALL SELECT 'fact_leave', COUNT(*) FROM warehouse.fact_leave UNION ALL SELECT 'fact_payroll', COUNT(*) FROM warehouse.fact_payroll ORDER BY table_name;"
```

## Run the 3 SQL checks
Copy `sql/task2_validation_queries.sql` into the project `sql/` folder, then:

```powershell
docker compose cp .\sql\task2_validation_queries.sql postgres:/tmp/task2_validation_queries.sql
docker compose exec -T postgres psql -U pulseiq_user -d pulseiq_warehouse -v ON_ERROR_STOP=1 -f /tmp/task2_validation_queries.sql
```

Compare Q1 with `reconciliation_answer_key.csv`, Q2 with `fact_headcount_monthly.csv`, and Q3 with `fact_attendance_monthly.csv` in `data/clean/`. Compare using the same month and department; allow only rounding differences for displayed decimal values.

## Diagram
Open `documentation/star_schema.mmd` in a Mermaid-compatible preview. The `.mmd` source is the saved schema diagram source for Task 2.
