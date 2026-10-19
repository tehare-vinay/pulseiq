# PulseIQ Analytics — Task 1: ETL Pipeline

## Objective
Load the supplied PulseIQ CSV files, transform and validate the data, and save clean outputs and run logs.

## Project requirements
- Python and pandas
- Pandera for data validation
- PyArrow for Parquet support
- Docker and Docker Compose

## Run the ETL pipeline
From the project root, run:

    docker compose run --rm etl

## Folders
- data/raw: original source CSV files
- data/clean: cleaned output files
- data/rejected: records rejected during processing
- logs: ETL run logs and validation reports

## Data protection
Keep source files unchanged. Do not publish company data or individual salary records.

## Validation
Review the generated run log, rejected records, validation report, and output row counts. A successful container build alone does not prove the data pipeline is correct.
