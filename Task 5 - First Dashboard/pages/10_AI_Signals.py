from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="AI Signals Dashboard",
    page_icon="AI",
    layout="wide",
)

st.title("AI Signals Dashboard")
st.caption("Task 14 | Anomaly detection and workforce forecasts")

st.info(
    "AI-generated, for human review. Signals support investigation "
    "and should not be treated as confirmed business decisions."
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "cloud_data_parquet"


@st.cache_data(ttl=300)
def load_parquet(dataset_name):
    """Load only named Parquet datasets from the cloud export folder."""
    allowed = {
        "cloud_anomaly_summary",
        "cloud_forecast_summary",
        "cloud_headcount_monthly_department",
    }
    if dataset_name not in allowed:
        raise ValueError("Dataset is not approved for this dashboard.")
    path = DATA_DIR / f"{dataset_name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Required cloud dataset not found: {path.name}")
    return pd.read_parquet(path)


def build_forecast_chart(
    actuals, forecasts, actual_column, title, y_title, note
):
    actual = actuals.copy()
    forecast = forecasts.copy()

    actual["month"] = pd.to_datetime(actual["month"], errors="coerce")
    forecast["forecast_month"] = pd.to_datetime(
        forecast["forecast_month"], errors="coerce"
    )

    for col in [actual_column]:
        actual[col] = pd.to_numeric(actual[col], errors="coerce")
    for col in ["forecast_value", "lower_80", "upper_80"]:
        forecast[col] = pd.to_numeric(forecast[col], errors="coerce")

    actual = actual.dropna(subset=["month", actual_column]).sort_values("month")
    forecast = forecast.dropna(
        subset=["forecast_month", "forecast_value", "lower_80", "upper_80"]
    ).sort_values("forecast_month")

    fig = go.Figure()

    if not actual.empty:
        fig.add_trace(go.Scatter(
            x=actual["month"], y=actual[actual_column],
            mode="lines+markers", name="Historical actual",
            line=dict(width=3),
        ))

    if not forecast.empty:
        fig.add_trace(go.Scatter(
            x=forecast["forecast_month"], y=forecast["lower_80"],
            mode="lines", line=dict(width=0),
            name="80% lower bound", showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_month"], y=forecast["upper_80"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(99, 110, 250, 0.18)",
            name="80% confidence range",
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_month"], y=forecast["forecast_value"],
            mode="lines+markers", name="AI forecast",
            line=dict(width=3, dash="dash"),
        ))

    fig.update_layout(
        title=title, height=430, xaxis_title="Month",
        yaxis_title=y_title, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0),
        margin=dict(l=40, r=30, t=85, b=40),
    )
    return fig, note


def make_error_table(actuals, forecasts):
    results = []
    actuals = actuals.copy()
    actuals["month"] = pd.to_datetime(actuals["month"], errors="coerce")

    for _, row in forecasts.iterrows():
        metric = row["metric"]
        month = pd.to_datetime(row["forecast_month"], errors="coerce")
        if pd.isna(month):
            continue

        if metric == "headcount_end":
            actual_col = "actual_headcount"
        elif metric == "attrition_rate_monthly_pct":
            actual_col = "actual_attrition_pct"
        else:
            continue

        matching = actuals[actuals["month"] == month]
        actual_value = (
            matching.iloc[0][actual_col] if not matching.empty else None
        )
        forecast_value = pd.to_numeric(row["forecast_value"], errors="coerce")

        if actual_value is not None and pd.notna(actual_value) and pd.notna(forecast_value):
            actual_value = float(actual_value)
            forecast_value = float(forecast_value)
            absolute_error = abs(actual_value - forecast_value)
            if metric == "headcount_end":
                error_type = "Absolute error (employees)"
                percentage_error = (
                    absolute_error / abs(actual_value) * 100
                    if actual_value != 0 else None
                )
            else:
                error_type = "Absolute error (percentage points)"
                percentage_error = None
            status = "CALCULATED"
        else:
            actual_value = None
            absolute_error = None
            percentage_error = None
            error_type = (
                "Employees" if metric == "headcount_end"
                else "Percentage points"
            )
            status = "ACTUAL_NOT_AVAILABLE"

        results.append({
            "Metric": metric,
            "Month": month.strftime("%Y-%m"),
            "Forecast": forecast_value,
            "Actual": actual_value,
            "Error type": error_type,
            "Absolute error": absolute_error,
            "Headcount error (%)": percentage_error,
            "Status": status,
        })

    return pd.DataFrame(results)


try:
    anomalies = load_parquet("cloud_anomaly_summary")
    forecasts = load_parquet("cloud_forecast_summary")
    headcount = load_parquet("cloud_headcount_monthly_department")

    # -----------------------------
    # 1. Anomaly analysis
    # -----------------------------
    st.header("1. Anomaly Analysis")
    st.caption("AI-generated, for human review")

    required_anomaly = {
        "source_dataset", "period", "anomaly_records",
        "flagged_records", "money_at_risk"
    }
    missing = required_anomaly - set(anomalies.columns)
    if missing:
        st.warning(f"Anomaly summary is missing columns: {', '.join(sorted(missing))}")
    elif anomalies.empty:
        st.warning("No anomaly summary records are available.")
    else:
        anomalies["anomaly_records"] = pd.to_numeric(
            anomalies["anomaly_records"], errors="coerce"
        ).fillna(0)
        anomalies["flagged_records"] = pd.to_numeric(
            anomalies["flagged_records"], errors="coerce"
        ).fillna(0)
        anomalies["money_at_risk"] = pd.to_numeric(
            anomalies["money_at_risk"], errors="coerce"
        ).fillna(0)

        total_anomalies = int(anomalies["anomaly_records"].sum())
        total_flagged = int(anomalies["flagged_records"].sum())
        total_risk = anomalies["money_at_risk"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Anomaly Records", f"{total_anomalies:,}")
        c2.metric("Flagged Records", f"{total_flagged:,}")
        c3.metric("Money at Risk", f"{total_risk:,.2f}")

        by_source = (
            anomalies.groupby("source_dataset", as_index=False)
            .agg(
                anomaly_records=("anomaly_records", "sum"),
                flagged_records=("flagged_records", "sum"),
                money_at_risk=("money_at_risk", "sum"),
            )
            .sort_values(["money_at_risk", "flagged_records"], ascending=False)
        )

        left, right = st.columns([3, 2])
        with left:
            fig_anomaly = go.Figure(go.Bar(
                x=by_source["money_at_risk"],
                y=by_source["source_dataset"],
                orientation="h",
                text=by_source["money_at_risk"].map(lambda x: f"{x:,.2f}"),
                textposition="auto",
            ))
            fig_anomaly.update_layout(
                title="Money at Risk by Source Dataset",
                xaxis_title="Money at Risk (source currency units)",
                yaxis_title="Source Dataset",
                height=max(400, len(by_source) * 45),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)
        with right:
            st.info(
                "The exported anomaly summary is aggregated by source dataset "
                "and period. It provides anomaly counts, flagged counts and "
                "money at risk; it does not contain reason codes or descriptions."
            )

        st.subheader("Anomaly Summary by Dataset and Period")
        display_anomalies = anomalies.rename(columns={
            "source_dataset": "Source Dataset",
            "period": "Period",
            "anomaly_records": "Anomaly Records",
            "flagged_records": "Flagged Records",
            "money_at_risk": "Money at Risk",
        })
        st.dataframe(display_anomalies, use_container_width=True, hide_index=True)

    st.divider()

    # -----------------------------
    # 2. Historical actuals
    # -----------------------------
    # Sum department-level workforce counts to create company-level actuals.
    hc = headcount.copy()
    required_hc = {
        "month_start_date", "headcount_start", "headcount_end", "exits"
    }
    missing_hc = required_hc - set(hc.columns)
    if missing_hc:
        raise ValueError(
            "Headcount export is missing required columns: "
            + ", ".join(sorted(missing_hc))
        )

    hc["month"] = pd.to_datetime(hc["month_start_date"], errors="coerce")
    for col in ["headcount_start", "headcount_end", "exits"]:
        hc[col] = pd.to_numeric(hc[col], errors="coerce").fillna(0)

    actuals = (
        hc.groupby("month", as_index=False)
        .agg(
            actual_headcount=("headcount_end", "sum"),
            starting_headcount=("headcount_start", "sum"),
            total_exits=("exits", "sum"),
        )
        .sort_values("month")
    )
    actuals["actual_attrition_pct"] = (
        100 * actuals["total_exits"]
        / actuals["starting_headcount"].replace(0, pd.NA)
    )

    # -----------------------------
    # 3. Headcount forecast
    # -----------------------------
    st.header("2. Headcount Forecast")
    st.caption("AI-generated, for human review")
    hc_forecast = forecasts[
        (forecasts["metric"] == "headcount_end")
        & (forecasts["department_id"].astype(str) == "ALL")
    ].copy()

    if hc_forecast.empty:
        st.warning("No company-level headcount forecast records are available.")
    else:
        fig, note = build_forecast_chart(
            actuals, hc_forecast, "actual_headcount",
            "Historical Headcount vs AI Forecast", "Employees",
            "Historical values show recorded ending headcount. Future values "
            "show the AI-generated forecast. The shaded region represents "
            "the stored 80% confidence range.",
        )
        left, right = st.columns([3, 1])
        with left:
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.info(note)

    st.divider()

    # -----------------------------
    # 4. Attrition forecast
    # -----------------------------
    st.header("3. Attrition Forecast")
    st.caption("AI-generated, for human review")
    attr_forecast = forecasts[
        (forecasts["metric"] == "attrition_rate_monthly_pct")
        & (forecasts["department_id"].astype(str) == "ALL")
    ].copy()

    if attr_forecast.empty:
        st.warning("No company-level attrition forecast records are available.")
    else:
        fig, note = build_forecast_chart(
            actuals, attr_forecast, "actual_attrition_pct",
            "Historical Attrition vs AI Forecast", "Attrition (%)",
            "Historical attrition is calculated as total exits divided by "
            "total starting headcount across departments. Future values are "
            "forecasts. The shaded region represents the stored 80% range.",
        )
        left, right = st.columns([3, 1])
        with left:
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.info(note)

    st.divider()

    # -----------------------------
    # 5. Forecast error analysis
    # -----------------------------
    st.header("4. Forecast Error Analysis")
    # Compare company-level actuals only with company-level (ALL) forecasts.
    # Department forecasts cannot be compared with company-wide actual totals.
    company_forecasts = forecasts[
        forecasts["department_id"].astype(str).str.upper() == "ALL"
    ].copy()
    error_table = make_error_table(actuals, company_forecasts)

    if error_table.empty:
        st.warning("No forecast error records are available.")
    else:
        st.info(
            "Errors are calculated only when actual data exists for the same "
            "forecast month. Headcount error is measured in employees; "
            "attrition error is measured in percentage points."
        )
        st.dataframe(error_table, use_container_width=True, hide_index=True)
        calculated = error_table[error_table["Status"] == "CALCULATED"]
        unavailable = error_table[
            error_table["Status"] == "ACTUAL_NOT_AVAILABLE"
        ]
        c1, c2 = st.columns(2)
        c1.metric("Errors Calculated", f"{len(calculated)}")
        c2.metric("Actuals Not Available", f"{len(unavailable)}")
        st.download_button(
            "Download Forecast Error Table",
            data=error_table.to_csv(index=False).encode("utf-8"),
            file_name="task14_forecast_error_table.csv",
            mime="text/csv",
        )

    # -----------------------------
    # Governance notes
    # -----------------------------
    st.divider()
    with st.expander("AI Signals - Data and Governance Notes"):
        st.write(
            "Anomaly analysis uses the privacy-safe exported summary, "
            "aggregated by source dataset and period."
        )
        st.write(
            "The export does not include anomaly reason codes, descriptions, "
            "individual anomaly rows, or counts of records with/without money. "
            "The dashboard therefore does not recreate those unavailable details."
        )
        st.write(
            "Forecast charts use department_id = ALL and the stored "
            "forecast_value, lower_80 and upper_80 fields."
        )
        st.write(
            "Historical actuals are calculated by summing the exported "
            "department-level headcount, starting headcount and exits by month."
        )
        st.write(
            "Forecast errors are not calculated for months without matching "
            "actual observations. AI-generated outputs require human review."
        )

except Exception as exc:
    st.error("AI Signals Dashboard could not be loaded.")
    st.exception(exc)
