from __future__ import annotations

import re
import pandas as pd
import plotly.express as px
import streamlit as st

from cloud_data import load_parquet

st.set_page_config(
    page_title="PulseIQ | Metric Explorer",
    page_icon="🔎",
    layout="wide"
)

st.title("PulseIQ | Metric Explorer")
st.caption("Task 18 | Step 3 — Company → Department → Team drill-down")

METRICS = {
    "Headcount": "metric_m01_headcount",
    "Hires": "metric_m02_hires",
    "Total Hires": "metric_m02_hires_total",
    "Exits": "metric_m03_exits",
    "Total Exits": "metric_m03_exits_total",
    "Monthly Attrition Rate": "metric_m04_attrition_rate",
    "Rolling 12-Month Attrition": "metric_m05_rolling_12m_attrition",
    "Voluntary Exits": "metric_m06_voluntary_attrition",
    "Exit Type Split": "metric_m07_exit_type_split",
    "Gross Pay": "metric_m07_gross_pay",
    "Net Pay": "metric_m08_net_pay",
    "Employer Payroll Cost": "metric_m09_payroll_cost",
    "Cost per Head": "metric_m10_cost_per_head",
    "Overtime Share": "metric_m11_overtime_share",
    "Variable Pay Share": "metric_m12_variable_pay_share",
    "Attendance Rate": "metric_m13_attendance_rate",
    "Late Arrival Rate": "metric_m14_late_arrival_rate",
    "Leave Without Pay Days": "metric_m15_lop_days",
    "Revenue": "metric_m16_revenue",
    "Net Profit": "metric_m17_net_profit",
    "Operating Margin": "metric_m18_operating_margin",
    "Payroll as % of Revenue": "metric_m19_payroll_pct_revenue",
    "Days Sales Outstanding (DSO)": "metric_m20_dso",
    "Overdue Receivables": "cloud_overdue_summary",
    "Task Completion Rate": "metric_m22_task_completion_rate",
    "On-time Delivery Rate": "metric_m23_on_time_delivery_rate",
    "Velocity": "metric_m24_velocity",
    "Average Cycle Time": "metric_m25_avg_cycle_time",
    "Anomaly Flag Rate": "metric_m26_anomaly_flag_rate",
    "High-risk Share": "metric_m27_high_risk_share",
    "Forecast Error (MAPE)": "metric_m28_forecast_error",
    "Headcount by Work Location": "metric_m29_headcount_by_work_location",
    "Headcount by Work Mode": "metric_m30_headcount_by_work_mode",
    "Headcount by Location Tier": "metric_m31_headcount_by_location_tier",
    "Overtime Hours": "metric_m32_overtime_hours",
    "Leave Days by Type and Status": "metric_m33_leave_days_by_type_status",
    "Monthly Department Headcount": "cloud_headcount_monthly_department",
    "Monthly Department Payroll": "cloud_payroll_monthly_department",
    "Team Sprint Productivity": "cloud_team_sprint_productivity",
    "Vendor Spend": "cloud_vendor_spend_summary",
    "Client Payment Summary": "cloud_client_payment_summary",
    "Monthly Cash Flow": "vw_task12_monthly_cash_flow",
    "Receivables Ageing": "vw_task12_receivables_ageing",
    "Monthly Profit & Loss": "vw_task11_monthly_pnl",
    "Expense by Category": "vw_task11_expense_by_category",
}

DIMENSION_HINTS = (
    "date", "month", "period", "quarter", "year",
    "department", "team", "sprint", "location", "mode",
    "tier", "client", "vendor", "account", "category",
    "bucket", "status", "type", "source", "metric",
    "industry", "city", "country", "state", "ageing",
)


def get_dimensions(frame):
    return [
        col for col in frame.columns
        if any(token in str(col).lower() for token in DIMENSION_HINTS)
    ]


def get_measures(frame):
    excluded = ("_id", "year", "month_number", "tier_number")
    return [
        col for col in frame.select_dtypes(include="number").columns
        if not any(token in str(col).lower() for token in excluded)
    ]


def clean_options(series):
    return sorted(series.dropna().astype(str).unique().tolist())


def get_minimum_group_size(dataset_name: str) -> int | None:
    """Read approved minimum group size from metric_catalog."""

    combined_metric_ids = {
        "cloud_headcount_monthly_department": {"M01"},
        "cloud_payroll_monthly_department": {"M07", "M09"},
        "cloud_team_sprint_productivity": {"M22", "M23", "M25"},
    }

    try:
        catalog = load_parquet("metric_catalog")
    except Exception:
        return None

    required = {"metric_id", "minimum_group_size"}

    if catalog.empty or not required.issubset(catalog.columns):
        return None

    wanted_ids = combined_metric_ids.get(dataset_name)

    if wanted_ids is None:
        match = re.search(r"M\d+", dataset_name.upper())
        if not match:
            return None
        wanted_ids = {match.group(0)}

    catalog = catalog.copy()

    catalog["_metric_ids"] = catalog["metric_id"].astype(str).str.upper().apply(
        lambda value: set(re.findall(r"M\d+", value))
    )

    matched = catalog[
        catalog["_metric_ids"].apply(
            lambda ids: bool(ids.intersection(wanted_ids))
        )
    ]

    if matched.empty:
        return None

    thresholds = []

    for value in matched["minimum_group_size"].dropna():
        # Supports values such as 5, "5 tasks", and "10 people".
        number = re.search(r"\d+", str(value))

        if number:
            threshold = int(number.group())

            if threshold > 0:
                thresholds.append(threshold)

    if not thresholds:
        return None

    return max(thresholds)

col1, col2 = st.columns(2)

with col1:
    metric_label = st.selectbox("Choose a metric", list(METRICS))

dataset_name = METRICS[metric_label]

try:
    df = load_parquet(dataset_name)
except Exception as exc:
    st.error(f"Unable to load {dataset_name}: {exc}")
    st.stop()

if df.empty:
    st.warning("No data is available for this metric.")
    st.stop()

dimensions = get_dimensions(df)
measures = get_measures(df)

if not dimensions or not measures:
    st.warning("This dataset does not contain both a supported dimension and numeric measure.")
    st.dataframe(df, use_container_width=True)
    st.stop()

with col2:
    dimension = st.selectbox("Choose a dimension", dimensions)

measure = st.selectbox("Choose the numeric value", measures)

# --------------------------------------------------
# STEP 3: COMPANY -> DEPARTMENT -> TEAM DRILL-DOWN
# --------------------------------------------------

st.subheader("Organizational Drill-down")

level = st.selectbox(
    "Choose drill-down level",
    ["Company", "Department", "Team"]
)

work = df.copy()

department_col = next(
    (c for c in work.columns if c.lower() == "department_id"),
    None
)

team_col = next(
    (c for c in work.columns if c.lower() == "team_id"),
    None
)

team_lookup = None
team_department_mapping = None

# Load the approved team dimension only when this dataset contains team_id.
if team_col:
    try:
        team_lookup = load_parquet("dim_team")
        if team_lookup is not None and not team_lookup.empty:
            lookup_columns = {str(c).lower(): c for c in team_lookup.columns}
            lookup_team_col = lookup_columns.get("team_id")
            lookup_department_col = lookup_columns.get("department_id")
            if lookup_team_col and lookup_department_col:
                mapping_columns = [lookup_team_col, lookup_department_col]
                lookup_active_col = lookup_columns.get("active_members")
                if lookup_active_col:
                    mapping_columns.append(lookup_active_col)
                rename_columns = {lookup_team_col: team_col, lookup_department_col: "department_id"}
                if lookup_active_col:
                    rename_columns[lookup_active_col] = "_privacy_population"
                team_department_mapping = (
                    team_lookup[mapping_columns]
                    .rename(columns=rename_columns)
                    .dropna(subset=[team_col, "department_id"])
                    .drop_duplicates(subset=[team_col])
                )
                # Exclude teams with conflicting department assignments.
                counts = team_department_mapping.groupby(team_col)["department_id"].nunique()
                ambiguous = set(counts[counts > 1].index.astype(str))
                if ambiguous:
                    team_department_mapping = team_department_mapping[
                        ~team_department_mapping[team_col].astype(str).isin(ambiguous)
                    ]
    except Exception:
        team_lookup = None
        team_department_mapping = None

if level == "Department":
    if department_col:
        departments = clean_options(work[department_col])

        if not departments:
            st.warning("No department values are available.")
            st.stop()

        selected_department = st.selectbox(
            "Choose department",
            departments
        )

        work = work[
            work[department_col].astype(str) == selected_department
        ]

    elif team_col and team_department_mapping is not None and not team_department_mapping.empty:
        work = work.merge(team_department_mapping, on=team_col, how="left", validate="many_to_one")
        work = work.dropna(subset=["department_id"])

        departments = clean_options(work["department_id"])

        if not departments:
            st.warning("No department mapping is available for this metric.")
            st.stop()

        selected_department = st.selectbox(
            "Choose department",
            departments
        )

        work = work[
            work["department_id"].astype(str) == selected_department
        ]

    else:
        st.warning(
            "Department-level drill-down is not available for this dataset "
            "because it has no department_id or verified team-to-department mapping."
        )
        st.stop()

elif level == "Team":
    if not team_col:
        st.warning(
            "Team-level drill-down is not available for this metric. "
            "Select a metric containing team_id."
        )
        st.stop()

    if team_department_mapping is not None and not team_department_mapping.empty:
        work = work.merge(team_department_mapping, on=team_col, how="left", validate="many_to_one")
        work = work.dropna(subset=["department_id"])

        departments = clean_options(work["department_id"])

        if not departments:
            st.warning("No department mapping is available.")
            st.stop()

        selected_department = st.selectbox(
            "Choose department",
            departments
        )

        work = work[
            work["department_id"].astype(str) == selected_department
        ]

    teams = clean_options(work[team_col])

    if not teams:
        st.warning("No teams are available for this selection.")
        st.stop()

    selected_team = st.selectbox("Choose team", teams)

    work = work[
        work[team_col].astype(str) == selected_team
    ]

else:
    st.info("Company level: displaying the complete company dataset.")

# --------------------------------------------------
# METRIC EXPLORER RESULTS
# --------------------------------------------------

if work.empty:
    st.info("No records are available for this drill-down selection.")
    st.stop()

# Preserve verified population fields before selecting chart columns.
work = work.copy()
work[measure] = pd.to_numeric(work[measure], errors="coerce")
work = work.dropna(subset=[dimension, measure])
if work.empty:
    st.info("No usable records are available for this selection.")
    st.stop()

# Step 4/5 privacy: count PEOPLE, never source rows. Use only population
# fields from approved aggregate exports / the approved team dimension.
population_col = next(
    (c for c in ["_privacy_population", "active_members", "headcount", "headcount_start", "headcount_end"] if c in work.columns),
    None
)

if population_col is None and dataset_name == "cloud_payroll_monthly_department":
    # Payroll exports are department/month aggregates; attach the matching
    # department-month headcount to determine the population represented.
    try:
        hc = load_parquet("cloud_headcount_monthly_department")
        if {"department_id", "month_start_date", "headcount_start"}.issubset(hc.columns) and {"department_id", "period_end_date"}.issubset(work.columns):
            hc = hc[["department_id", "month_start_date", "headcount_start"]].copy()
            hc["_month"] = pd.to_datetime(hc["month_start_date"], errors="coerce").dt.to_period("M")
            work["_month"] = pd.to_datetime(work["period_end_date"], errors="coerce").dt.to_period("M")
            work = work.merge(hc[["department_id", "_month", "headcount_start"]], on=["department_id", "_month"], how="left", validate="many_to_one")
            population_col = "headcount_start"
    except Exception:
        population_col = None

if population_col is None:
    st.warning(
        "Results are hidden because this dataset does not contain a verified people-count field. "
        "Source-row counts are not a valid privacy test."
    )
    st.stop()

work[population_col] = pd.to_numeric(work[population_col], errors="coerce")
# Unknown, zero, or negative population values cannot pass a privacy check.
work = work.dropna(subset=[population_col])
work = work[work[population_col] > 0]
if work.empty:
    st.info("No verified population data is available for this selection.")
    st.stop()

summary = (
    work.groupby(dimension, dropna=False)
    .agg(value=(measure, "sum"), minimum_people=(population_col, "min"))
    .reset_index()
)

# --------------------------------------------------
# STEP 4: MINIMUM GROUP-SIZE PRIVACY SUPPRESSION
# STEP 5: ADVERSARIAL FILTER TEST / LEAK PREVENTION
# --------------------------------------------------
minimum_group_size = get_minimum_group_size(dataset_name)

st.subheader(f"{metric_label} by {dimension}")
st.caption(
    f"Dataset: {dataset_name} | Drill-down level: {level} | "
    "Aggregated from the approved Parquet export."
)

if minimum_group_size is None:
    st.warning(
        "Privacy threshold could not be read from metric_catalog. "
        "Results are hidden until an approved minimum group size is available."
    )
    st.stop()

# Conservative rule: if any underlying period has fewer than the minimum
# number of people, hide the whole displayed group. This prevents narrow
# filters from exposing 1- or 2-person groups.
visible_summary = summary[summary["minimum_people"] >= minimum_group_size].copy()
suppressed_count = len(summary) - len(visible_summary)

if visible_summary.empty:
    st.info(
        f"No results are displayed because every selected group has fewer than "
        f"{minimum_group_size} people. Choose a broader drill-down level or another metric."
    )
    st.stop()

if suppressed_count:
    st.warning(
        f"{suppressed_count} group(s) hidden because their verified population is "
        f"below {minimum_group_size} people."
    )
else:
    st.caption(
        f"Privacy check passed: every displayed group has at least "
        f"{minimum_group_size} people."
    )

# Display only privacy-screened aggregate results; never expose underlying rows.
visible_summary = visible_summary.drop(columns=["minimum_people"])

k1, k2 = st.columns(2)

k1.metric("Visible groups", f"{len(visible_summary):,}")
k2.metric("Visible total", f"{visible_summary['value'].sum():,.2f}")

chart = px.bar(
    visible_summary,
    x=dimension,
    y="value",
    title=f"{measure} by {dimension}"
)

chart.update_layout(
    xaxis_title=dimension,
    yaxis_title=measure
)

st.plotly_chart(chart, use_container_width=True)

st.subheader("Results")
st.dataframe(visible_summary, use_container_width=True, hide_index=True)
