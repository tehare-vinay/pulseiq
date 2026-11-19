# Task 19 – Metrics API Deployment Documentation

## 1. Deployment overview

The PulseIQ Metrics API is deployed as a separate service on Render. The dashboard remains hosted separately on Streamlit Community Cloud. Both applications use the PulseIQ GitHub repository as their source repository.

| Item | Deployment detail |
|---|---|
| Project | PulseIQ Analytics |
| GitHub repository | https://github.com/tehare-vinay/pulseiq |
| Repository branch | `master` |
| API hosting platform | Render |
| API service URL | https://pulseiq-api-nbb0.onrender.com |
| Interactive API documentation | https://pulseiq-api-nbb0.onrender.com/docs |
| OpenAPI schema | https://pulseiq-api-nbb0.onrender.com/openapi.json |
| Dashboard hosting | Streamlit Community Cloud |
| API framework | FastAPI |
| ASGI server | Uvicorn |

## 2. Render service configuration

The API was configured on Render with the following settings:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Root directory | Blank (repository root) |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Free |
| Database configuration | `DATABASE_URL` environment variable configured in Render |

**Security note:** The database connection string is stored as a Render environment variable. Do not place its actual value in this document, GitHub, screenshots, or other public files.

## 3. Deployment source and application entry point

The API is maintained in the same GitHub repository as the dashboard:

`https://github.com/tehare-vinay/pulseiq`

The deployment configuration uses the repository root as the service root and starts the FastAPI application through:

`src.api.main:app`

The deployment record in the project history shows API source files, including `src/api/main.py` and `src/api/__init__.py`, pushed to the `master` branch. A recorded commit associated with that push is `8cf225c`. Confirm the exact deployed commit in the Render Events page before treating that hash as the final production deployment revision.

## 4. API endpoints

Base URL:

`https://pulseiq-api-nbb0.onrender.com`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API root/health response |
| GET | `/api/v1/metrics` | Returns the available metrics |
| GET | `/api/v1/metrics/{metric_id}` | Returns one metric by its ID |

Interactive endpoint details and schemas are available at:

`https://pulseiq-api-nbb0.onrender.com/docs`

OpenAPI schema:

`https://pulseiq-api-nbb0.onrender.com/openapi.json`

## 5. Exposed metrics

The following five metrics were selected for Task 19:

| Metric ID | Metric name | Source table | Metric view |
|---|---|---|---|
| M01 | Headcount | `fact_headcount_monthly` | `metric_m01_headcount` |
| M03 | Exits | `fact_headcount_monthly` | `metric_m03_exits` |
| M09 | Payroll Cost | `fact_payroll` | `metric_m09_payroll_cost` |
| M16 | Revenue | `fact_ledger` | `metric_m16_revenue` |
| M22 | Task Completion Rate | `fact_task` | `metric_m22_task_completion_rate` |

Each metric endpoint returns its metric ID, metric name, value, definition, source, source view, and freshness information. The API responses also include a period where applicable.

## 6. Deployment verification

The deployed API was tested through the Swagger UI. The recorded verification results were:

| Test | Result recorded |
|---|---|
| API service status | Render service reported Live |
| Swagger UI (`/docs`) | Opened successfully |
| `GET /` | HTTP 200 |
| `GET /api/v1/metrics` | HTTP 200; five selected metrics returned |
| `GET /api/v1/metrics/M01` | HTTP 200 |
| `GET /api/v1/metrics/M03` | HTTP 200 |
| `GET /api/v1/metrics/M09` | HTTP 200 |
| `GET /api/v1/metrics/M16` | HTTP 200 |
| `GET /api/v1/metrics/M22` | HTTP 200 |

Example request:

```bash
curl -X GET "https://pulseiq-api-nbb0.onrender.com/api/v1/metrics/M03" \
  -H "accept: application/json"
```

The recorded M03 response returned HTTP 200 and included the metric name `Exits`, source `fact_headcount_monthly`, source view `metric_m03_exits`, a value, a definition, and freshness fields.

## 7. Data freshness statement

The API responses expose freshness metadata such as `last_refresh` and `freshness_note`. The response examples inspected during Task 19 reported the latest ETL batch as the freshness basis. For M22, the response explicitly noted that its `last_refresh` value represented the latest task creation date and was not a confirmed ETL refresh timestamp.

Consumers should therefore read the freshness fields returned for each metric and should not interpret a task creation date as a verified ETL refresh time.

## 8. How to access and use the API

1. Open the API Swagger page: https://pulseiq-api-nbb0.onrender.com/docs
2. Expand `GET /api/v1/metrics/{metric_id}`.
3. Select **Try it out**.
4. Enter one of the metric IDs: `M01`, `M03`, `M09`, `M16`, or `M22`.
5. Select **Execute**.
6. Check the HTTP status and JSON response, including the definition, source, source view, and freshness fields.

## 9. Operational notes

- The API is deployed separately from the Streamlit dashboard.
- The API and dashboard source code are maintained in the same GitHub repository.
- Render must receive its database connection through the `DATABASE_URL` environment variable.
- Keep credentials and connection strings out of source control and documentation.
- After a deployment, check the Render service Events/logs and repeat the endpoint tests above.
- A successful API response confirms that the endpoint responded; it does not by itself prove that every underlying source table has been refreshed recently.

## 10. Evidence to retain for the Task 19 report

Retain screenshots showing:

1. Render service status as **Live**.
2. Render service settings showing the runtime, build command, and start command. Hide secret environment-variable values.
3. The Swagger UI at `/docs`.
4. Successful `200` responses for the five metric endpoints.
5. The GitHub repository and branch used by the Render service.

---

**Task:** 19 – Metrics API and Data Lineage
**Step documented:** 6 – Deploy the API and document the deployment
**Documentation file:** `docs/task19/Deployment_Documentation.md`
