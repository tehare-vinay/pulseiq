# PulseIQ Phase 1 — Task 1 ETL update

## What changed
- Preserves the existing conservative cleaning and validation logic.
- Discovers the official PulseIQ exports, excluding the README and duplicate payroll export.
- Reads the official `data_contracts.csv`; checks required contract columns and `nullable=no` rules for explicitly covered feeds.
- Writes `documentation/task1_data_contract_notes.md` describing contract coverage and limitations.
- Writes a per-run `logs/etl_row_count_summary.csv` with input/output/duplicate/rejected counts.
- Writes `logs/etl_database_load_report.json` so database load cannot be mistaken as successful when skipped or failed.
- Optional PostgreSQL loading uses one transaction and `TRUNCATE` + reload for repeatability; source files are never modified.
- Rejected exact duplicates include `_source_file` and `_rejection_reason`.

## Important caveats
- The supplied contract file lists only four feed types. Tables without contract entries do not receive invented contracts; the notes document this limitation.
- A local test of the selected-files ZIP completed twice across 32 CSVs with 62,997 input rows and 62,997 output rows per run, zero exact duplicate rows in this export, and two distinct run IDs in append-only history.
- PostgreSQL loading was explicitly `SKIPPED` in the isolated test environment because local database credentials were not available. Therefore, database loading is not marked complete until the script is run against the user's local PostgreSQL service.
- Pandera was not installed in the isolated test environment; install Task 1 requirements in the project's virtual environment before treating the schema validation result as final.

## PostgreSQL environment variables
Set these in the PowerShell session (use values from your local, non-committed environment):
- `PULSEIQ_PGHOST` (default `localhost`)
- `PULSEIQ_PGPORT` (default `5432`)
- `PULSEIQ_PGDATABASE`
- `PULSEIQ_PGUSER`
- `PULSEIQ_PGPASSWORD`

Do not commit passwords or `.env` files.
