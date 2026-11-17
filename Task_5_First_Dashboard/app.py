from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from cloud_data import load_parquet

st.set_page_config(
    page_title="PulseIQ | Workforce",
    page_icon="📊",
    layout="wide",
)

st.title("PulseIQ | Workforce & Headcount")
st.markdown(
    "<p style='font-size:18px; color:#B8C0CC; margin-top:-8px;'>"
    "Phase 1 dashboard — Data is sourced from privacy-safe exports of governed metric views."
    "</p>",
    unsafe_allow_html=True,
)

# These names must match the approved Parquet exports in cloud_data_parquet/.
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

DATE_CANDIDATES = [
    "month_start_date", "period_end_date", "month", "period",
    "posting_period", "period_start", "date",
]
DEPT_CANDIDATES = ["department_name", "department", "dept_name", "department_id"]


@st.cache_data(ttl=300, show_spinner="Loading governed workforce datasets...")
def read_metric(dataset_name: str) -> pd.DataFrame:
    """Load only a named, approved Parquet export; no database connection is used."""
    if dataset_name not in METRICS.values():
        raise ValueError(f"Dataset is not approved for this dashboard: {dataset_name}")
    return load_parquet(dataset_name)


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df.empty:
        return None
    by_lower = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]
    for col in df.columns:
        name = str(col).lower()
        if any(candidate.lower() in name for candidate in candidates):
            return col
    return None


def numeric_value_col(df: pd.DataFrame, metric_label: str) -> str | None:
    """Choose the metric value column explicitly where possible."""
    preferred = {
        "Headcount": ["headcount"],
        "Hires": ["hires", "hire_count", "new_hires"],
        "Exits": ["exits", "exit_count"],
        "Attrition": ["attrition_rate_pct", "attrition_rate", "monthly_attrition_pct"],
        "Hires total": ["hires", "total_hires", "hire_count"],
        "Exits total": ["exits", "total_exits", "exit_count"],
        "Location tier": ["headcount", "employee_count", "count"],
        "Work mode": ["headcount", "employee_count", "count"],
    }.get(metric_label, [])
    col = find_col(df, preferred)
    if col is not None and pd.api.types.is_numeric_dtype(df[col]):
        return col

    excluded = {"department_id", "team_id", "year", "month_number"}
    numeric_cols = [
        col for col in df.select_dtypes(include="number").columns
        if str(col).lower() not in excluded
    ]
    return numeric_cols[-1] if numeric_cols else None


def normalize_period(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    normalized = parsed.dt.strftime("%Y-%m-%d")
    # Preserve non-date period labels if a source uses a YYYY-MM string.
    return normalized.fillna(series.astype(str).str.strip())


def apply_filters(
    df: pd.DataFrame, selected_department: str, selected_period: str
) -> pd.DataFrame:
    out = df.copy()
    department_col = find_col(out, DEPT_CANDIDATES)
    period_col = find_col(out, DATE_CANDIDATES)

    if department_col and selected_department != "All departments":
        out = out[out[department_col].astype(str) == selected_department]
    if period_col and selected_period != "All dates":
        out = out[normalize_period(out[period_col]) == selected_period]
    return out


def latest_period_rows(df: pd.DataFrame, selected_period: str) -> pd.DataFrame:
    if df.empty:
        return df
    period_col = find_col(df, DATE_CANDIDATES)
    if period_col is None:
        return df
    out = df.copy()
    out["__period_key"] = normalize_period(out[period_col])
    target = selected_period if selected_period != "All dates" else out["__period_key"].max()
    out = out[out["__period_key"] == target].drop(columns="__period_key")
    return out


def format_metric(df: pd.DataFrame, label: str, rate: bool = False) -> str:
    if df.empty:
        return "Unavailable"
    value_col = numeric_value_col(df, label)
    if value_col is None:
        return "Unavailable"
    values = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if values.empty:
        return "Unavailable"
    value = values.mean() if rate else values.sum()
    return f"{value:,.2f}%" if rate else f"{value:,.0f}"


# Load all approved datasets independently so a missing optional view does not hide the others.
frames: dict[str, pd.DataFrame] = {}
errors: dict[str, str] = {}
for label, dataset in METRICS.items():
    try:
        frames[label] = read_metric(dataset)
    except Exception as exc:
        errors[label] = str(exc).splitlines()[0]

if errors:
    with st.expander("Dataset availability details"):
        for label, message in errors.items():
            st.warning(f"{label}: {message}")

headcount = frames.get("Headcount", pd.DataFrame())
hires = frames.get("Hires", pd.DataFrame())
exits = frames.get("Exits", pd.DataFrame())
attrition = frames.get("Attrition", pd.DataFrame())
location_tier = frames.get("Location tier", pd.DataFrame())
work_mode = frames.get("Work mode", pd.DataFrame())

if headcount.empty:
    st.error("Headcount dataset is unavailable. Check cloud_data_parquet/metric_m01_headcount.parquet.")
    st.stop()

# Filters are based on dimensions actually present in the exported headcount dataset.
dept_col = find_col(headcount, DEPT_CANDIDATES)
date_col = find_col(headcount, DATE_CANDIDATES)
department_values = (
    sorted(headcount[dept_col].dropna().astype(str).unique().tolist())
    if dept_col else []
)
period_values = (
    sorted(normalize_period(headcount[date_col]).dropna().unique().tolist())
    if date_col else []
)

filter_left, filter_right = st.columns(2)
with filter_left:
    selected_department = st.selectbox("Department", ["All departments", *department_values])
with filter_right:
    selected_period = st.selectbox("Month/date", ["All dates", *period_values])

st.caption(
    f"Department: {selected_department} | Period: "
    f"{selected_period if selected_period != 'All dates' else 'Latest available for KPI cards'}"
)

# KPI cards. The total views are used only for the all-department selection.
hires_kpi = frames.get("Hires total", hires) if selected_department == "All departments" else hires
exits_kpi = frames.get("Exits total", exits) if selected_department == "All departments" else exits
kpi_specs = [
    ("Current headcount", headcount, "Headcount", False),
    ("Monthly joiners", hires_kpi, "Hires total" if selected_department == "All departments" else "Hires", False),
    ("Monthly exits", exits_kpi, "Exits total" if selected_department == "All departments" else "Exits", False),
    ("Monthly attrition", attrition, "Attrition", True),
]
kpi_columns = st.columns(4)
for column, (label, source, metric_label, is_rate) in zip(kpi_columns, kpi_specs):
    selected = apply_filters(source, selected_department, selected_period)
    selected = latest_period_rows(selected, selected_period)
    with column:
        st.metric(label, format_metric(selected, metric_label, rate=is_rate))

# 1. Headcount trend
st.subheader("Headcount trend")
hc_filtered = apply_filters(headcount, selected_department, selected_period)
hc_period_col = find_col(hc_filtered, DATE_CANDIDATES)
hc_value_col = numeric_value_col(hc_filtered, "Headcount")
if not hc_filtered.empty and hc_period_col and hc_value_col:
    trend = hc_filtered.copy()
    trend["Period"] = normalize_period(trend[hc_period_col])
    trend["Headcount"] = pd.to_numeric(trend[hc_value_col], errors="coerce")
    trend = trend.groupby("Period", as_index=False)["Headcount"].sum().sort_values("Period")
    if not trend.empty:
        change = float(trend["Headcount"].iloc[-1] - trend["Headcount"].iloc[0])
        if change > 0:
            insight = f"Headcount increased by {change:,.0f} across the displayed period."
        elif change < 0:
            insight = f"Headcount decreased by {abs(change):,.0f} across the displayed period."
        else:
            insight = "Headcount remained unchanged across the displayed period."
        st.plotly_chart(px.line(trend, x="Period", y="Headcount", markers=True, title=insight), use_container_width=True)
        st.info(f"Finding: {insight}")
    else:
        st.info("No headcount trend rows are available for the selected filters.")
else:
    st.info("Headcount trend is unavailable for the available dataset columns.")

# 2. Department breakdown and 3. Location-tier chart
left, right = st.columns(2)
with left:
    st.subheader("Department breakdown")
    dept_data = latest_period_rows(hc_filtered, selected_period)
    dept_value_col = numeric_value_col(dept_data, "Headcount")
    dept_dimension_col = find_col(dept_data, DEPT_CANDIDATES)
    if not dept_data.empty and dept_dimension_col and dept_value_col:
        dept_chart = dept_data.copy()
        dept_chart[dept_value_col] = pd.to_numeric(dept_chart[dept_value_col], errors="coerce")
        dept_chart = dept_chart.groupby(dept_dimension_col, as_index=False)[dept_value_col].sum()
        dept_chart = dept_chart.sort_values(dept_value_col, ascending=False)
        if not dept_chart.empty:
            top = dept_chart.iloc[0]
            title = f"{top[dept_dimension_col]} has the highest displayed headcount ({top[dept_value_col]:,.0f})"
            st.plotly_chart(px.bar(dept_chart, x=dept_dimension_col, y=dept_value_col, title=title), use_container_width=True)
            st.info(f"Finding: {title}.")
        else:
            st.info("No department values are available for the selected period.")
    else:
        st.info("Department breakdown is unavailable for the selected period.")

with right:
    st.subheader("Headcount by location tier")
    tier_dimension_col = find_col(location_tier, ["location_tier", "city_tier", "tier"])
    tier_value_col = numeric_value_col(location_tier, "Location tier")
    if not location_tier.empty and tier_dimension_col and tier_value_col:
        tier_chart = location_tier.copy()
        tier_chart[tier_value_col] = pd.to_numeric(tier_chart[tier_value_col], errors="coerce")
        tier_chart = tier_chart.dropna(subset=[tier_value_col]).groupby(tier_dimension_col, as_index=False)[tier_value_col].sum()
        tier_chart = tier_chart.sort_values(tier_value_col, ascending=False)
        if not tier_chart.empty:
            top = tier_chart.iloc[0]
            title = f"{top[tier_dimension_col]} has the highest location-tier headcount ({top[tier_value_col]:,.0f})"
            st.plotly_chart(px.bar(tier_chart, x=tier_dimension_col, y=tier_value_col, title=title), use_container_width=True)
            st.info(f"Finding: {title}.")
        else:
            st.info("No publishable location-tier values are available.")
    else:
        st.info("Location-tier dataset is unavailable or does not expose the required aggregate columns.")

# 4. Work-mode chart
st.subheader("Headcount by work mode")
mode_dimension_col = find_col(work_mode, ["work_mode", "workmode", "work_arrangement", "work_type"])
mode_value_col = numeric_value_col(work_mode, "Work mode")
if not work_mode.empty and mode_dimension_col and mode_value_col:
    mode_chart = work_mode.copy()
    mode_chart[mode_value_col] = pd.to_numeric(mode_chart[mode_value_col], errors="coerce")
    mode_chart = mode_chart.dropna(subset=[mode_value_col]).groupby(mode_dimension_col, as_index=False)[mode_value_col].sum()
    mode_chart = mode_chart.sort_values(mode_value_col, ascending=False)
    if not mode_chart.empty:
        top = mode_chart.iloc[0]
        title = f"{top[mode_dimension_col]} leads with {top[mode_value_col]:,.0f} active employees"
        st.plotly_chart(px.bar(mode_chart, x=mode_dimension_col, y=mode_value_col, title=title), use_container_width=True)
        st.info(f"Finding: {title}.")
    else:
        st.info("No publishable work-mode values are available.")
else:
    st.info("Work-mode dataset is unavailable or does not expose the required aggregate columns.")

with st.expander("Data and governance notes"):
    st.write(
        "This dashboard reads only the approved Parquet exports listed in METRICS. "
        "It does not connect to PostgreSQL or query raw fact/dimension tables at runtime."
    )
    st.write(
        "Department and date filters apply only where the exported dataset contains those dimensions. "
        "Location-tier and work-mode datasets are aggregate views and may not respond to these filters."
    )
    st.write("Only privacy-safe, governed aggregate exports should be placed in cloud_data_parquet/.")
    for label, df in frames.items():
        st.write(f"**{label}** — {len(df):,} rows; columns: {', '.join(map(str, df.columns))}")
