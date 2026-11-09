import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "Task 5 - First Dashboard" / ".env", override=True)

st.set_page_config(
    page_title="PulseIQ | Workforce",
    page_icon="ðŸ“Š",
    layout="wide",
)

st.title("PulseIQ | Workforce & Headcount")
st.markdown(
    "<p style='font-size:18px; color:#B8C0CC; margin-top:-8px;'>"
    "Phase 1 dashboard â€” Data Is Sourced From Governed Metric Views Only."
    "</p>",
    unsafe_allow_html=True,
)

# Only approved, database-governed metric views are queried by this app.
METRICS = {
    "Headcount": "metric_m01_headcount",
    "Hires": "metric_m02_hires",
    "Exits": "metric_m03_exits",
    "Attrition": "metric_m04_attrition_rate",
    "Hires total": "metric_m02_hires_total",
    "Exits total": "metric_m03_exits_total",
    "Location tier": "metric_m31_headcount_by_location_tier",
    "Work mode": "metric_m30_headcount_by_work_mode",
}


@st.cache_data(ttl=120)
def read_view(view_name: str) -> pd.DataFrame:
    """Read a hard-coded, approved metric view from PostgreSQL."""
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )
    try:
        return pd.read_sql_query(
            f'SELECT * FROM public."{view_name}" LIMIT 50000', conn
        )
    finally:
        conn.close()


def find_col(df: pd.DataFrame, options: list[str]):
    """Find a column by exact name first, then by partial name."""
    lower = {str(col).lower(): col for col in df.columns}
    for option in options:
        if option.lower() in lower:
            return lower[option.lower()]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(option.lower() in col_lower for option in options):
            return col
    return None


def numeric_col(df: pd.DataFrame):
    """Return the last numeric column, normally the metric value."""
    cols = list(df.select_dtypes(include="number").columns)
    return cols[-1] if cols else None


def filtered(df: pd.DataFrame, selected_dept: str, selected_date: str):
    """Apply only filters supported by the view's available columns."""
    out = df.copy()
    department_col = find_col(
        out, ["department_name", "department", "dept_name", "department_id"]
    )
    period_col = find_col(
        out, ["month_start_date", "month_start", "month", "period_start", "date"]
    )

    if selected_dept != "All departments" and department_col:
        out = out[out[department_col].astype(str) == selected_dept]
    if selected_date != "All dates" and period_col:
        out = out[out[period_col].astype(str) == selected_date]
    return out


def latest_period_data(df: pd.DataFrame, selected_date: str):
    """Return the selected period, or the latest available period."""
    if df.empty:
        return df
    period_col = find_col(
        df, ["month_start_date", "month_start", "month", "period_start", "date"]
    )
    if period_col is None:
        return df
    out = df.copy()
    out[period_col] = out[period_col].astype(str)
    if selected_date != "All dates":
        return out[out[period_col] == selected_date]
    latest_period = out[period_col].max()
    return out[out[period_col] == latest_period]


def kpi_value(df: pd.DataFrame, metric_type: str = "sum") -> str:
    """Format a KPI while respecting suppressed/null metric values."""
    if df.empty:
        return "Unavailable"
    value_col = numeric_col(df)
    if value_col is None:
        return "Unavailable"
    raw_values = pd.to_numeric(df[value_col], errors="coerce")
    if raw_values.isna().any():
        return "Suppressed"
    values = raw_values.dropna()
    if values.empty:
        return "Unavailable"
    if metric_type == "rate":
        return f"{values.mean():.2f}%"
    return f"{values.sum():,.0f}"


# Load approved metric views and display diagnostics if any are unavailable.
frames, errors = {}, {}
for label, view_name in METRICS.items():
    try:
        frames[label] = read_view(view_name)
    except Exception as exc:
        errors[label] = str(exc).splitlines()[0]

if errors:
    with st.expander("Metric views unavailable â€” diagnostics"):
        for label, message in errors.items():
            st.warning(f"{label}: {message}")

if not frames:
    st.error(
        "No governed metric views could be read. Check the database connection and view names."
    )
    st.stop()

headcount = frames.get("Headcount", pd.DataFrame())
hires = frames.get("Hires", pd.DataFrame())
exits = frames.get("Exits", pd.DataFrame())
attrition = frames.get("Attrition", pd.DataFrame())
location_tier_df = frames.get("Location tier", pd.DataFrame())
work_mode_df = frames.get("Work mode", pd.DataFrame())

# Filters are populated from the headcount view.
dept_col = find_col(
    headcount, ["department_name", "department", "dept_name", "department_id"]
)
date_col = find_col(
    headcount, ["month_start_date", "month_start", "month", "period_start", "date"]
)

dept_values = (
    sorted(headcount[dept_col].dropna().astype(str).unique()) if dept_col else []
)
date_values = (
    sorted(headcount[date_col].dropna().astype(str).unique()) if date_col else []
)

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    selected_dept = st.selectbox(
        "Department", ["All departments"] + dept_values
    )
with filter_col2:
    selected_date = st.selectbox("Month/date", ["All dates"] + date_values)

# Four KPI cards.
hires_kpi = (
    frames.get("Hires total", hires)
    if selected_dept == "All departments"
    else hires
)
exits_kpi = (
    frames.get("Exits total", exits)
    if selected_dept == "All departments"
    else exits
)

kpis = [
    ("Current headcount", headcount, "sum"),
    ("Monthly joiners", hires_kpi, "sum"),
    ("Monthly exits", exits_kpi, "sum"),
    ("Monthly attrition", attrition, "rate"),
]
kpi_cols = st.columns(4)
for column, (label, df, metric_type) in zip(kpi_cols, kpis):
    with column:
        selected_df = filtered(df, selected_dept, selected_date)
        period_df = latest_period_data(selected_df, selected_date)
        st.metric(label, kpi_value(period_df, metric_type))

# 1. Headcount trend: title states the observed finding.
st.subheader("Headcount trend")
hc = filtered(headcount, selected_dept, selected_date)
hc_date = find_col(
    hc, ["month_start_date", "month_start", "month", "period_start", "date"]
)
hc_value = numeric_col(hc)

if not hc.empty and hc_date and hc_value:
    trend = hc.groupby(hc_date, dropna=False)[hc_value].sum().reset_index()
    trend.columns = ["Period", "Headcount"]
    trend = trend.sort_values("Period")
    if not trend.empty:
        change = trend["Headcount"].iloc[-1] - trend["Headcount"].iloc[0]
        if change > 0:
            trend_title = f"Headcount grew by {change:,.0f} across the displayed period"
        elif change < 0:
            trend_title = f"Headcount fell by {abs(change):,.0f} across the displayed period"
        else:
            trend_title = "Headcount stayed level across the displayed period"
        st.plotly_chart(
            px.line(
                trend,
                x="Period",
                y="Headcount",
                markers=True,
                title=trend_title,
            ),
            use_container_width=True,
        )
        st.markdown(
    f"<p style='font-size:16px; color:#D1D5DB; margin-top:8px;'>"
    f"<b>Finding:</b> Headcount grew by {change:,.0f} across the displayed period.</p>",
    unsafe_allow_html=True,
)
    else:
        st.info("No headcount trend rows are available for the selected filters.")
else:
    st.info("Headcount trend is unavailable for the current view schema.")

# 2. Department breakdown and 3. Location-tier chart.
left, right = st.columns(2)
with left:
    st.subheader("Department breakdown")
    dept_data = latest_period_data(hc, selected_date)
    dcol = find_col(
        dept_data,
        ["department_name", "department", "dept_name", "department_id"],
    )
    dept_value = numeric_col(dept_data)

    if not dept_data.empty and dcol and dept_value:
        dept = (
            dept_data.groupby(dcol)[dept_value]
            .sum()
            .reset_index()
            .sort_values(dept_value, ascending=False)
        )
        if not dept.empty:
            top_department = dept.iloc[0]
            department_title = (
                f"{top_department[dcol]} has the largest displayed headcount "
                f"({top_department[dept_value]:,.0f})"
            )
            st.plotly_chart(
                px.bar(
                    dept,
                    x=dcol,
                    y=dept_value,
                    title=department_title,
                ),
                use_container_width=True,
            )
            st.markdown(
    f"<p style='font-size:16px; color:#D1D5DB; margin-top:8px;'>"
    f"<b>Finding:</b> {top_department[dept_col]} has the largest displayed headcount "
    f"({top_department[dept_value]:,.0f}).</p>",
    unsafe_allow_html=True,
)
        else:
            st.info("No department values are available for the selected period.")
    else:
        st.info("Department breakdown is unavailable for the selected period.")

with right:
    st.subheader("Location tier")
    tier_col = find_col(location_tier_df, ["location_tier", "city_tier"])
    tier_value = find_col(location_tier_df, ["headcount", "employee_count", "count"])

    if not location_tier_df.empty and tier_col and tier_value:
        tier_data = location_tier_df.copy()
        tier_data[tier_value] = pd.to_numeric(tier_data[tier_value], errors="coerce")
        tier_data = tier_data.dropna(subset=[tier_value]).sort_values(
            tier_value, ascending=False
        )
        if not tier_data.empty:
            top_tier = tier_data.iloc[0]
            tier_title = (
                f"{top_tier[tier_col]} has the highest active headcount "
                f"({top_tier[tier_value]:,.0f})"
            )
            st.plotly_chart(
                px.bar(tier_data, x=tier_col, y=tier_value, title=tier_title),
                use_container_width=True,
            )
            st.markdown(
    f"<p style='font-size:16px; color:#D1D5DB; margin-top:8px;'>"
    f"<b>Finding:</b> {top_tier[tier_col]} has {top_tier[tier_value]:,.0f} active employees "
    f"in the governed location-tier view.</p>",
    unsafe_allow_html=True,
)
        else:
            st.info("No publishable location-tier values are available.")
    else:
        st.info("Location-tier metric view is unavailable.")

# 4. Work-mode chart.
st.subheader("Headcount by work mode")
mode_col = find_col(work_mode_df, ["work_mode", "workmode", "work_arrangement"])
mode_value = find_col(work_mode_df, ["headcount", "employee_count", "count"])

if not work_mode_df.empty and mode_col and mode_value:
    wm = work_mode_df.copy()
    wm[mode_value] = pd.to_numeric(wm[mode_value], errors="coerce")
    wm = wm.dropna(subset=[mode_value]).sort_values(mode_value, ascending=False)
    if not wm.empty:
        top_mode = wm.iloc[0]
        total_mode_headcount = wm[mode_value].sum()
        share = (
            top_mode[mode_value] / total_mode_headcount * 100
            if total_mode_headcount
            else 0
        )
        mode_title = (
            f"{top_mode[mode_col]} leads with "
            f"{top_mode[mode_value]:,.0f} active employees"
        )
        st.plotly_chart(
            px.bar(wm, x=mode_col, y=mode_value, title=mode_title),
            use_container_width=True,
        )
        st.markdown(
    f"<p style='font-size:16px; color:#D1D5DB; margin-top:8px;'>"
    f"<b>Finding:</b> {top_mode[mode_col]} leads with "
    f"{top_mode[mode_value]:,.0f} active employees.</p>",
    unsafe_allow_html=True,
)
    else:
        st.info("No publishable work-mode values are available.")
else:
    st.info("Work-mode data is unavailable. Check the governed metric view.")

with st.expander("Data and governance notes"):
    st.write(
        "The dashboard queries only the governed metric views listed in the METRICS mapping. "
        "It does not query raw fact or dimension tables directly."
    )
    st.write(
        "The location-tier and work-mode metric views should include current active employees "
        "and enforce a minimum group size of five in the database."
    )
    st.write(
        "Department/date filters apply to charts only when those dimensions are present in "
        "the corresponding metric view. The location-tier and work-mode views are aggregate "
        "views and therefore do not respond to these filters unless those dimensions are exposed."
    )
    for label, df in frames.items():
        st.write(
            f"**{label}** â€” {len(df):,} rows; columns: {', '.join(map(str, df.columns))}"
        )


