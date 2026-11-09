import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Existing project environment
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="AI Signals Dashboard",
    page_icon="AI",
    layout="wide",
)

st.title("AI Signals Dashboard")
st.caption("Task 14 | Anomaly detection and workforce forecasts")

st.info(
    "AI-generated, for human review. "
    "Signals support investigation and should not be treated "
    "as confirmed business decisions."
)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


@st.cache_data(ttl=300)
def read_query(query):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def load_anomalies():
    query = """
    WITH cleaned AS (
        SELECT
            reason_code,
            reason_text,
            NULLIF(
                REGEXP_REPLACE(
                    BTRIM(money_at_risk::text),
                    '[^0-9.-]',
                    '',
                    'g'
                ),
                ''
            ) AS cleaned_money
        FROM public.fact_anomaly
        WHERE UPPER(BTRIM(flagged::text)) = 'Y'
    ),

    normalized AS (
        SELECT
            reason_code,
            reason_text,
            CASE
                WHEN cleaned_money ~ '^-?[0-9]+(\\.[0-9]+)?$'
                THEN cleaned_money::numeric
                ELSE NULL
            END AS money_value
        FROM cleaned
    )

    SELECT
        reason_code AS anomaly_type,
        MAX(reason_text) AS description,
        COUNT(*) AS anomaly_count,

        COUNT(*) FILTER (
            WHERE money_value IS NOT NULL
              AND money_value <> 0
        ) AS records_with_money,

        COUNT(*) FILTER (
            WHERE money_value IS NULL
               OR money_value = 0
        ) AS records_without_money,

        COALESCE(SUM(money_value), 0)
            AS total_money_at_risk

    FROM normalized
    GROUP BY reason_code
    ORDER BY total_money_at_risk DESC, anomaly_count DESC;
    """

    return read_query(query)


@st.cache_data(ttl=300)
def load_forecasts():
    query = """
    SELECT
        metric,
        department_id,
        forecast_month::date AS forecast_month,
        forecast_value::numeric AS forecast_value,
        lower_80::numeric AS lower_80,
        upper_80::numeric AS upper_80,
        method,
        trained_through,
        model_version
    FROM public.fact_forecast
    WHERE department_id = 'ALL'
      AND metric IN (
          'headcount_end',
          'attrition_rate_monthly_pct'
      )
    ORDER BY metric, forecast_month;
    """
    return read_query(query)


@st.cache_data(ttl=300)
def load_actuals():
    query = """
    SELECT
        month_start_date::date AS month,
        SUM(NULLIF(BTRIM(headcount_end), '')::numeric)
            AS actual_headcount,
        SUM(NULLIF(BTRIM(headcount_start), '')::numeric)
            AS starting_headcount,
        SUM(NULLIF(BTRIM(exits), '')::numeric)
            AS total_exits,
        ROUND(
            100.0 * SUM(NULLIF(BTRIM(exits), '')::numeric)
            / NULLIF(
                SUM(NULLIF(BTRIM(headcount_start), '')::numeric),
                0
            ),
            2
        ) AS actual_attrition_pct
    FROM public.fact_headcount_monthly
    GROUP BY month_start_date::date
    ORDER BY month;
    """
    return read_query(query)


def build_forecast_chart(
    actuals,
    forecasts,
    actual_column,
    title,
    y_title,
    note,
):
    actual = actuals.copy()
    forecast = forecasts.copy()

    actual["month"] = pd.to_datetime(actual["month"])
    forecast["forecast_month"] = pd.to_datetime(
        forecast["forecast_month"]
    )

    actual[actual_column] = pd.to_numeric(
        actual[actual_column], errors="coerce"
    )
    for col in ["forecast_value", "lower_80", "upper_80"]:
        forecast[col] = pd.to_numeric(
            forecast[col], errors="coerce"
        )

    actual = actual.dropna(
        subset=["month", actual_column]
    ).sort_values("month")

    forecast = forecast.dropna(
        subset=["forecast_month", "forecast_value",
                "lower_80", "upper_80"]
    ).sort_values("forecast_month")

    fig = go.Figure()

    if not actual.empty:
        fig.add_trace(
            go.Scatter(
                x=actual["month"],
                y=actual[actual_column],
                mode="lines+markers",
                name="Historical actual",
                line=dict(width=3),
            )
        )

    if not forecast.empty:
        fig.add_trace(
            go.Scatter(
                x=forecast["forecast_month"],
                y=forecast["lower_80"],
                mode="lines",
                line=dict(width=0),
                name="80% lower bound",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=forecast["forecast_month"],
                y=forecast["upper_80"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(99, 110, 250, 0.18)",
                name="80% confidence range",
                hovertemplate=(
                    "Month: %{x|%b %Y}<br>"
                    "Upper: %{y:.2f}<extra></extra>"
                ),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=forecast["forecast_month"],
                y=forecast["forecast_value"],
                mode="lines+markers",
                name="AI forecast",
                line=dict(width=3, dash="dash"),
            )
        )

    fig.update_layout(
        title=title,
        height=430,
        xaxis_title="Month",
        yaxis_title=y_title,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=40, r=30, t=85, b=40),
    )

    return fig, note


def make_error_table(actuals, forecasts):
    results = []

    for _, row in forecasts.iterrows():
        metric = row["metric"]
        month = pd.Timestamp(row["forecast_month"])

        if metric == "headcount_end":
            actual_col = "actual_headcount"
        elif metric == "attrition_rate_monthly_pct":
            actual_col = "actual_attrition_pct"
        else:
            continue

        matching = actuals[
            pd.to_datetime(actuals["month"]) == month
        ]

        actual_value = (
            matching.iloc[0][actual_col]
            if not matching.empty
            else None
        )

        forecast_value = float(row["forecast_value"])

        if pd.notna(actual_value):
            actual_value = float(actual_value)
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
                "Employees"
                if metric == "headcount_end"
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
    anomalies = load_anomalies()
    forecasts = load_forecasts()
    actuals = load_actuals()

    # -----------------------------
    # 1. Anomaly analysis
    # -----------------------------
    st.header("1. Anomaly Analysis")

    st.caption(
        "AI-generated, for human review"
    )

    if anomalies.empty:
        st.warning("No flagged anomaly records are available.")
    else:
        anomalies["total_money_at_risk"] = pd.to_numeric(
            anomalies["total_money_at_risk"],
            errors="coerce"
        ).fillna(0)

        anomalies = anomalies.sort_values(
            ["total_money_at_risk", "anomaly_count"],
            ascending=[False, False]
        )

        total_anomalies = int(anomalies["anomaly_count"].sum())
        total_risk = anomalies["total_money_at_risk"].sum()

        c1, c2 = st.columns(2)

        c1.metric("Flagged Anomalies", f"{total_anomalies:,}")
        c2.metric("Total Money at Risk", f"{total_risk:,.2f}")

        fig_anomaly = go.Figure(
            go.Bar(
                x=anomalies["total_money_at_risk"],
                y=anomalies["anomaly_type"],
                orientation="h",
                text=anomalies["total_money_at_risk"].map(
                    lambda x: f"{x:,.2f}"
                ),
                textposition="auto",
            )
        )

        fig_anomaly.update_layout(
            title="Anomaly Types Ranked by Money at Risk",
            xaxis_title="Money at Risk (source currency units)",
            yaxis_title="Anomaly Type",
            height=max(400, len(anomalies) * 45),
            yaxis=dict(autorange="reversed"),
        )

        left, right = st.columns([3, 2])

        with left:
            st.plotly_chart(
                fig_anomaly,
                use_container_width=True
            )

        with right:
            st.info(
                "Plain-language note: Anomaly types at the top "
                "have the highest recorded monetary exposure. "
                "Records without a monetary value remain included "
                "in the anomaly count but do not contribute "
                "to money at risk."
            )

        st.subheader("Anomaly Details")

        display_anomalies = anomalies.rename(columns={
            "anomaly_type": "Anomaly Type",
            "description": "Description",
            "anomaly_count": "Anomaly Count",
            "records_with_money": "Records With Money",
            "records_without_money": "Records Without Money",
            "total_money_at_risk": "Total Money at Risk",
        })

        st.dataframe(
            display_anomalies,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # -----------------------------
    # 2. Headcount forecast
    # -----------------------------
    st.header("2. Headcount Forecast")

    st.caption("AI-generated, for human review")

    hc_forecast = forecasts[
        forecasts["metric"] == "headcount_end"
    ].copy()

    if hc_forecast.empty:
        st.warning("No headcount forecast records are available.")
    else:
        fig, note = build_forecast_chart(
            actuals,
            hc_forecast,
            "actual_headcount",
            "Historical Headcount vs AI Forecast",
            "Employees",
            "Historical values show recorded ending headcount. "
            "Future values show the AI-generated forecast. "
            "The shaded region represents the 80% confidence range."
        )

        left, right = st.columns([3, 1])

        with left:
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.info(note)

    st.divider()

    # -----------------------------
    # 3. Attrition forecast
    # -----------------------------
    st.header("3. Attrition Forecast")

    st.caption("AI-generated, for human review")

    attr_forecast = forecasts[
        forecasts["metric"] == "attrition_rate_monthly_pct"
    ].copy()

    if attr_forecast.empty:
        st.warning("No attrition forecast records are available.")
    else:
        fig, note = build_forecast_chart(
            actuals,
            attr_forecast,
            "actual_attrition_pct",
            "Historical Attrition vs AI Forecast",
            "Attrition (%)",
            "Historical attrition is calculated from total exits "
            "divided by total starting headcount. Future values "
            "are forecasts. The shaded region represents the "
            "80% confidence range."
        )

        left, right = st.columns([3, 1])

        with left:
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.info(note)

    st.divider()

    # -----------------------------
    # 4. Forecast error table
    # -----------------------------
    st.header("4. Forecast Error Analysis")

    error_table = make_error_table(actuals, forecasts)

    if error_table.empty:
        st.warning("No forecast error records are available.")
    else:
        st.info(
            "Forecast errors are calculated only when actual data "
            "exists for the same forecast month. Headcount error "
            "is measured in employees; attrition error is measured "
            "in percentage points. Percentage error is shown only "
            "for headcount."
        )

        st.dataframe(
            error_table,
            use_container_width=True,
            hide_index=True,
        )

        calculated = error_table[
            error_table["Status"] == "CALCULATED"
        ]

        unavailable = error_table[
            error_table["Status"] == "ACTUAL_NOT_AVAILABLE"
        ]

        c1, c2 = st.columns(2)

        c1.metric(
            "Errors Calculated",
            f"{len(calculated)}"
        )

        c2.metric(
            "Actuals Not Available",
            f"{len(unavailable)}"
        )

        csv = error_table.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Forecast Error Table",
            data=csv,
            file_name="task14_forecast_error_table.csv",
            mime="text/csv",
        )

    # -----------------------------
    # Governance notes
    # -----------------------------
    st.divider()

    with st.expander("AI Signals - Data and Governance Notes"):
        st.write(
            "Anomaly records are restricted to flagged Y records "
            "and grouped by reason code."
        )

        st.write(
            "Anomaly money at risk is the sum of available "
            "money_at_risk values. Blank monetary values are "
            "not treated as known monetary exposure."
        )

        st.write(
            "Forecast charts use the ALL department forecast. "
            "Historical actuals use all 11 departments, including "
            "D00 (Executive Office)."
        )

        st.write(
            "The 80% confidence range is displayed using the "
            "stored lower_80 and upper_80 values."
        )

        st.write(
            "Forecast errors are not calculated for months "
            "without matching actual observations."
        )

        st.write(
            "AI-generated outputs require human review and "
            "do not establish confirmed anomalies or future outcomes."
        )

except Exception as exc:
    st.error("AI Signals Dashboard could not be loaded.")
    st.exception(exc)
