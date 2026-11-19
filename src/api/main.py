import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(
    title="PulseIQ Metrics API",
    description="API for governed PulseIQ business metrics and data lineage.",
    version="1.0.0",
)

METRICS = {
    "M01": {
        "name": "Headcount",
        "view": "metric_m01_headcount",
        "source": "fact_headcount_monthly",
        "definition": "Active employees on the last day of the month.",
        "period": "month_start_date",
        "value_column": "headcount",
        "refresh_type": "etl_batch",
    },
    "M03": {
        "name": "Exits",
        "view": "metric_m03_exits_total",
        "source": "fact_headcount_monthly",
        "definition": "Employees whose exit date falls in the month.",
        "period": "month_start_date",
        "value_column": "exits",
        "refresh_type": "etl_batch",
    },
    "M09": {
        "name": "Payroll Cost",
        "view": "metric_m09_payroll_cost",
        "source": "fact_payroll",
        "definition": "Full employer cost, including gross pay and employer contributions.",
        "period": "period_end_date",
        "value_column": "employer_cost",
        "refresh_type": "etl_batch",
    },
    "M16": {
        "name": "Revenue",
        "view": "metric_m16_revenue",
        "source": "fact_ledger",
        "definition": "Income booked in the ledger from accounts 4001 to 4004.",
        "period": "posting_period",
        "value_column": "revenue",
        "refresh_type": "etl_batch",
    },
    "M22": {
        "name": "Task Completion Rate",
        "view": "metric_m22_task_completion_rate",
        "source": "fact_task",
        "definition": "Completed tasks divided by non-cancelled planned tasks.",
        "period": None,
        "value_column": "completion_rate_pct",
        "refresh_type": "record_date",
    },
}


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(
            database_url,
            connect_timeout=10,
        )

    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise RuntimeError(
            "DATABASE_URL or POSTGRES_PASSWORD is not configured."
        )

    return psycopg2.connect(
        host=os.getenv("API_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "pulseiq_warehouse"),
        user=os.getenv("POSTGRES_USER", "pulseiq_user"),
        password=password,
        connect_timeout=10,
    )


def get_freshness(cursor, metric):
    source = metric["source"]

    if metric["refresh_type"] == "etl_batch":
        cursor.execute(
            f"""
            SELECT
                etl_year AS latest_year,
                etl_month AS latest_month
            FROM public.{source}
            WHERE etl_year IS NOT NULL
              AND etl_month IS NOT NULL
            ORDER BY etl_year DESC, etl_month DESC
            LIMIT 1
            """
        )

        row = cursor.fetchone()

        if not row:
            return {
                "last_refresh": None,
                "freshness_note": "ETL batch information unavailable",
            }

        return {
            "last_refresh": (
                f'{row["latest_year"]}-'
                f'{str(row["latest_month"]).zfill(2)}'
            ),
            "freshness_note": "Latest ETL batch available",
        }

    cursor.execute(
        """
        SELECT MAX(created_date) AS latest_created
        FROM public.fact_task
        """
    )

    row = cursor.fetchone()
    latest_created = row["latest_created"] if row else None

    return {
        "last_refresh": (
            latest_created.isoformat()
            if hasattr(latest_created, "isoformat")
            else str(latest_created)
            if latest_created is not None
            else None
        ),
        "freshness_note": (
            "Latest record creation date; "
            "not a confirmed ETL refresh timestamp"
        ),
    }


def get_metric_value(cursor, metric_id, metric):
    view = metric["view"]

    if metric_id == "M22":
        cursor.execute(
            f"""
            SELECT
                SUM(completed_tasks) AS completed_tasks,
                SUM(total_tasks) AS total_tasks,
                CASE
                    WHEN SUM(total_tasks) > 0
                    THEN ROUND(
                        100.0 * SUM(completed_tasks)::numeric
                        / SUM(total_tasks), 2
                    )
                    ELSE NULL
                END AS value
            FROM public.{view}
            """
        )
        return cursor.fetchone()

    value_column = metric["value_column"]
    period_column = metric["period"]

    cursor.execute(
        f"""
        SELECT
            {period_column} AS period,
            SUM({value_column}) AS value
        FROM public.{view}
        WHERE {value_column} IS NOT NULL
          AND {period_column} IS NOT NULL
        GROUP BY {period_column}
        HAVING SUM({value_column}) IS NOT NULL
        ORDER BY {period_column} DESC
        LIMIT 1
        """
    )

    return cursor.fetchone()


@app.get("/")
def root():
    return {
        "message": "PulseIQ Metrics API is running",
        "docs": "/docs",
        "available_metrics": list(METRICS.keys()),
    }


@app.get("/api/v1/metrics")
def list_metrics():
    return {
        "count": len(METRICS),
        "metrics": [
            {
                "metric_id": metric_id,
                "metric_name": metric["name"],
                "definition": metric["definition"],
                "source": metric["source"],
                "view": metric["view"],
            }
            for metric_id, metric in METRICS.items()
        ],
    }


@app.get("/api/v1/metrics/{metric_id}")
def get_metric(metric_id: str):
    metric_id = metric_id.upper()

    if metric_id not in METRICS:
        raise HTTPException(
            status_code=404,
            detail="Unknown metric ID",
        )

    metric = METRICS[metric_id]

    try:
        with get_connection() as connection:
            with connection.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                result = get_metric_value(
                    cursor,
                    metric_id,
                    metric,
                )

                freshness = get_freshness(cursor, metric)

        if not result or result["value"] is None:
            raise HTTPException(
                status_code=404,
                detail="No metric data available for the latest period",
            )

        response = {
            "metric_id": metric_id,
            "metric_name": metric["name"],
            "value": result["value"],
            "definition": metric["definition"],
            "source": metric["source"],
            "source_view": metric["view"],
            "last_refresh": freshness["last_refresh"],
            "freshness_note": freshness["freshness_note"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if metric_id == "M22":
            response["completed_tasks"] = result["completed_tasks"]
            response["total_tasks"] = result["total_tasks"]

        else:
            period_value = result["period"]

            if hasattr(period_value, "isoformat"):
                response["period"] = period_value.isoformat()
            else:
                response["period"] = (
                    str(period_value)
                    if period_value is not None
                    else None
                )

        return response

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Metric retrieval failed: {str(error)}",
        )
