# Task 19 — Step 5: PulseIQ Metrics API Documentation

## 1. Overview

The PulseIQ Metrics API provides access to five governed business metrics. It returns metric values, definitions, source information, reporting periods, and data freshness details.

**API title:** PulseIQ Metrics API
**Version:** 1.0.0
**Base URL:** `http://127.0.0.1:8000`
**Interactive API documentation:** `http://127.0.0.1:8000/docs`

## 2. Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Checks API status and lists available metric IDs |
| GET | `/api/v1/metrics` | Returns the list of available metrics |
| GET | `/api/v1/metrics/{metric_id}` | Returns details and the latest value for a selected metric |

## 3. Available Metrics

| Metric ID | Metric Name | Source Table |
|---|---|---|
| M01 | Headcount | `fact_headcount_monthly` |
| M03 | Exits | `fact_headcount_monthly` |
| M09 | Payroll Cost | `fact_payroll` |
| M16 | Revenue | `fact_ledger` |
| M22 | Task Completion Rate | `fact_task` |

## 4. API Usage Examples

### Example 1 — Check API Status

**Request:**

```bash
curl.exe http://127.0.0.1:8000/
```

**Example response:**

```json
{
  "message": "PulseIQ Metrics API is running",
  "docs": "/docs",
  "available_metrics": ["M01", "M03", "M09", "M16", "M22"]
}
```

### Example 2 — List Available Metrics

**Request:**

```bash
curl.exe http://127.0.0.1:8000/api/v1/metrics
```

**Example response structure:**

```json
{
  "count": 5,
  "metrics": [
    {
      "metric_id": "M01",
      "metric_name": "Headcount",
      "definition": "Active employees on the last day of the month.",
      "source": "fact_headcount_monthly",
      "view": "metric_m01_headcount"
    }
  ]
}
```

The endpoint returns the complete list of five configured metrics.

### Example 3 — Get a Metric

**Request:**

```bash
curl.exe http://127.0.0.1:8000/api/v1/metrics/M03
```

**Example response:**

```json
{
  "metric_id": "M03",
  "metric_name": "Exits",
  "value": 6,
  "definition": "Employees whose exit date falls in the month.",
  "source": "fact_headcount_monthly",
  "source_view": "metric_m03_exits_total",
  "last_refresh": "2026-09",
  "freshness_note": "Latest ETL batch available",
  "generated_at": "2026-11-19T12:52:25.680818+00:00",
  "period": "2026-07-01T00:00:00"
}
```

The example shows the response captured during API testing. Values and timestamps may change when the API is queried again.

### Example 4 — Get Other Metrics

Use the same endpoint with a different metric ID.

```bash
curl.exe http://127.0.0.1:8000/api/v1/metrics/M01
curl.exe http://127.0.0.1:8000/api/v1/metrics/M09
curl.exe http://127.0.0.1:8000/api/v1/metrics/M16
curl.exe http://127.0.0.1:8000/api/v1/metrics/M22
```

## 5. Response Field Description

| Field | Description |
|---|---|
| `metric_id` | Unique metric identifier |
| `metric_name` | Name of the metric |
| `value` | Latest calculated metric value |
| `definition` | Business definition of the metric |
| `source` | Source fact table |
| `source_view` | Metric view used by the API |
| `last_refresh` | Latest available ETL batch month or record creation date |
| `freshness_note` | Explanation of the freshness information |
| `generated_at` | UTC timestamp when the API response was generated |
| `period` | Reporting period for the metric, when applicable |
| `completed_tasks` | Completed task count, returned for M22 |
| `total_tasks` | Total non-cancelled planned task count, returned for M22 |

## 6. Data Freshness

The API provides three fields related to data freshness:

- **`last_refresh`** — For ETL-based metrics, this represents the latest available ETL year and month. For M22, it represents the latest task record creation date.
- **`freshness_note`** — Clarifies the meaning and limitation of the refresh information.
- **`generated_at`** — Records the UTC time when the API response was generated.

For M22, the record creation date is not a confirmed ETL refresh timestamp. The API explicitly communicates this limitation through `freshness_note`.

## 7. Error Responses

| HTTP Status | Description |
|---|---|
| 404 | Unknown metric ID or no metric data available for the latest period |
| 422 | Validation error for an invalid request |
| 500 | Metric retrieval failed due to an unexpected error |

**Example — Unknown metric:**

```json
{
  "detail": "Unknown metric ID"
}
```

## 8. Interactive Documentation

The API also provides Swagger UI for testing endpoints interactively.

Open:

`http://127.0.0.1:8000/docs`

Select an endpoint, click **Try it out**, enter the required metric ID if applicable, and click **Execute** to view the response.

## 9. Conclusion

The PulseIQ Metrics API documentation describes the available endpoints, five supported metrics, request examples, response fields, data freshness information, and error responses. The API provides a simple interface for retrieving governed business metrics.
