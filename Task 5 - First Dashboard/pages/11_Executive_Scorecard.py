import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv


# ---------------------------------------------------------------------
# PulseIQ | Task 15 - Executive Scorecard
# Step 3 requirement: value, target, trend and traffic-light status
# for every KPI. Step 5: A4 print layout. Step 6: detailed-page links.
# All KPI values are read from governed metric views.
# Targets are read only from the governed target table; no target is
# invented when the source does not provide one.
# ---------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="PulseIQ | Executive Scorecard",
    page_icon="📊",
    layout="wide",
)

# Step 5 - A4 print layout. These rules affect printing only; the
# interactive dashboard layout and KPI calculations remain unchanged.
st.markdown(
    """
    <style>
    @media print {
        @page {
            size: A4 landscape;
            margin: 8mm;
        }

        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stMain"], .main {
            width: 100% !important;
            min-width: 0 !important;
            background: #ffffff !important;
            color: #111111 !important;
            overflow: visible !important;
        }

        [data-testid="stSidebar"], header, footer,
        [data-testid="stToolbar"], [data-testid="stStatusWidget"],
        [data-testid="stExpander"] {
            display: none !important;
        }

        .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        h1 {
            font-size: 20pt !important;
            line-height: 1.15 !important;
            margin: 0 0 2mm 0 !important;
            color: #111111 !important;
        }

        h2 {
            font-size: 13pt !important;
            margin: 2mm 0 !important;
            color: #111111 !important;
        }

        p, label, [data-testid="stCaptionContainer"] {
            font-size: 8pt !important;
            line-height: 1.2 !important;
            color: #333333 !important;
        }

        [data-testid="stAlert"] {
            padding: 2mm 3mm !important;
            margin: 1mm 0 2mm 0 !important;
            border: 1px solid #b8c4d1 !important;
            background: #f2f5f8 !important;
            color: #111111 !important;
        }

        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 3mm !important;
            align-items: stretch !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }

        [data-testid="column"] {
            min-width: 0 !important;
            width: 25% !important;
            flex: 1 1 25% !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #aeb6bf !important;
            border-radius: 2mm !important;
            padding: 2mm !important;
            margin-bottom: 2mm !important;
            background: #ffffff !important;
            color: #111111 !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }

        [data-testid="stMetric"] {
            padding: 0 !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 8pt !important;
            color: #333333 !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 17pt !important;
            line-height: 1.1 !important;
            color: #111111 !important;
        }

        [data-testid="stMarkdownContainer"] {
            color: #111111 !important;
        }

        hr {
            margin: 2mm 0 !important;
        }

        * {
            box-shadow: none !important;
            text-shadow: none !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("PulseIQ | Executive Company-Health Scorecard")
st.caption("Task 15 | Executive KPI overview")
st.info("KPI values are sourced from governed metric views.")

# name: view, preferred date column, aggregation, unit, direction,
#       value-column candidates
METRICS = {
    "Headcount": {
        "view": "metric_m01_headcount",
        "period": "month_start_date",
        "aggregation": "sum",
        "unit": "count",
        "direction": "context",
        "value_candidates": ["headcount", "employee_count", "total_headcount"],
    },
    "Attrition Rate": {
        "view": "metric_m04_attrition_rate",
        "period": "month_start_date",
        "aggregation": "mean",
        "unit": "percent",
        "direction": "lower",
        "value_candidates": ["attrition_rate_pct", "attrition_rate", "monthly_attrition_rate_pct"],
    },
    "Payroll Cost": {
        "view": "metric_m09_payroll_cost",
        "period": "period_end_date",
        "aggregation": "sum",
        "unit": "INR",
        "direction": "lower",
        "value_candidates": ["employer_cost", "total_employer_cost", "payroll_cost", "gross_pay"],
    },
    "Attendance Rate": {
        "view": "metric_m13_attendance_rate",
        "period": "period_end_date",
        "aggregation": "mean",
        "unit": "percent",
        "direction": "higher",
        "value_candidates": ["attendance_rate_pct", "attendance_rate"],
    },
    "Net Profit": {
        "view": "metric_m17_net_profit",
        "period": "posting_period",
        "aggregation": "sum",
        "unit": "INR",
        "direction": "higher",
        "value_candidates": ["net_profit", "profit_after_tax", "profit"],
    },
    "Operating Margin": {
        "view": "metric_m18_operating_margin",
        "period": "posting_period",
        "aggregation": "ratio",
        "unit": "percent",
        "direction": "higher",
        "value_candidates": [],
    },
    "Overdue Receivables": {
        "view": "metric_m21_overdue_receivables",
        "period": None,
        "aggregation": "sum",
        "unit": "INR",
        "direction": "lower",
        "value_candidates": [
            "overdue_receivables",
            "overdue_amount",
            "overdue_balance",
            "overdue_invoice_amount",
            "total_overdue_amount",
            "receivables_overdue",
        ],
    },
    "Task Completion Rate": {
        "view": "metric_m22_task_completion_rate",
        "period": None,
        "aggregation": "ratio",
        "unit": "percent",
        "direction": "higher",
        "value_candidates": [],
    },
}

# Step 6 - Link each Executive KPI to its existing detailed page.
# Paths are relative to the Streamlit entrypoint in Task 5 - First Dashboard.
KPI_DETAIL_PAGES = {
    "Headcount": ("app.py", "View workforce details"),
    "Attrition Rate": ("pages/3_Attrition_Analytics.py", "View attrition details"),
    "Payroll Cost": ("pages/5_Payroll_Cost.py", "View payroll details"),
    "Attendance Rate": ("pages/2_Attendance_Trends.py", "View attendance details"),
    "Net Profit": ("pages/5_Profit_Loss.py", "View profit and loss details"),
    "Operating Margin": ("pages/5_Profit_Loss.py", "View profit and loss details"),
    "Overdue Receivables": ("pages/8_Receivables_Cash_Flow.py", "View receivables details"),
    "Task Completion Rate": ("pages/4_Team_Productivity.py", "View team productivity details"),
}

PERIOD_CANDIDATES = [
    "month_start_date",
    "period_start_date",
    "period_end_date",
    "snapshot_date",
    "as_of_date",
    "reporting_date",
    "report_date",
    "month",
    "posting_period",
    "period",
    "created_month",
]

# Target columns are matched against the actual columns in
# public.metric_kpi_targets. A missing target remains unconfigured.
TARGET_CANDIDATES = {
    "Headcount": [
        "headcount_target", "target_headcount", "headcount_target_count",
    ],
    "Attrition Rate": [
        "attrition_monthly_target_pct", "attrition_rate_target",
        "attrition_target_pct",
    ],
    "Payroll Cost": [
        "payroll_cost_target", "employer_cost_target",
        "payroll_target_amount",
    ],
    "Attendance Rate": [
        "attendance_rate_target", "attendance_target_pct",
    ],
    "Net Profit": [
        "net_profit_target", "profit_target",
    ],
    "Operating Margin": [
        "operating_margin_target_pct", "operating_margin_target",
    ],
    "Overdue Receivables": [
        "overdue_receivables_target", "overdue_amount_target",
        "receivables_target",
    ],
    "Task Completion Rate": [
        "task_completion_target_pct", "task_completion_target",
    ],
}


def db_connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=8,
    )


@st.cache_data(ttl=120)
def read_view(view_name):
    # view_name is selected only from the fixed METRICS configuration.
    conn = db_connect()
    try:
        return pd.read_sql_query(
            f'SELECT * FROM public."{view_name}"',
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=120)
def read_target_table():
    """Read target table without assuming optional target columns exist."""
    conn = db_connect()
    try:
        return pd.read_sql_query(
            'SELECT * FROM public."metric_kpi_targets"',
            conn,
        )
    finally:
        conn.close()


def normalized_lookup(columns):
    return {str(column).strip().lower(): column for column in columns}


def choose_column(df, candidates):
    lookup = normalized_lookup(df.columns)
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def find_period_column(metric_name, df):
    preferred = METRICS[metric_name]["period"]
    lookup = normalized_lookup(df.columns)

    if preferred and preferred.lower() in lookup:
        return lookup[preferred.lower()]

    for candidate in PERIOD_CANDIDATES:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def numeric_series(df, column):
    return pd.to_numeric(df[column], errors="coerce")


def calculate_metric_value(metric_name, df):
    """Calculate the metric from columns actually exposed by its view."""
    cfg = METRICS[metric_name]
    aggregation = cfg["aggregation"]

    if aggregation == "ratio" and metric_name == "Operating Margin":
        revenue_col = choose_column(df, ["revenue", "total_revenue", "sales_revenue"])
        profit_col = choose_column(df, ["net_profit", "operating_profit", "operating_income"])
        if revenue_col is None or profit_col is None:
            raise ValueError(
                "Operating Margin view must expose revenue and net_profit/"
                "operating_profit columns."
            )
        revenue = numeric_series(df, revenue_col).sum(min_count=1)
        profit = numeric_series(df, profit_col).sum(min_count=1)
        if pd.isna(revenue) or revenue == 0 or pd.isna(profit):
            return None
        return float(profit / revenue * 100)

    if aggregation == "ratio" and metric_name == "Task Completion Rate":
        completed_col = choose_column(
            df, ["completed_tasks", "tasks_completed", "completed_count"]
        )
        total_col = choose_column(
            df, ["total_tasks", "task_count", "total_task_count"]
        )

        # Some governed views expose a pre-calculated rate instead.
        rate_col = choose_column(
            df, ["task_completion_rate_pct", "completion_rate_pct",
                 "task_completion_pct", "completion_rate"]
        )
        if completed_col and total_col:
            completed = numeric_series(df, completed_col).sum(min_count=1)
            total = numeric_series(df, total_col).sum(min_count=1)
            if pd.isna(completed) or pd.isna(total) or total <= 0:
                return None
            return float(completed / total * 100)
        if rate_col:
            values = numeric_series(df, rate_col).dropna()
            return float(values.mean()) if not values.empty else None
        raise ValueError(
            "Task Completion view must expose completed_tasks and total_tasks, "
            "or a governed completion-rate column."
        )

    value_col = choose_column(df, cfg["value_candidates"])

    # Safe fallback for overdue receivables: choose only a numeric column
    # whose name clearly represents an overdue receivable amount.
    if value_col is None and metric_name == "Overdue Receivables":
        for column in df.columns:
            name = str(column).lower()
            if (
                ("overdue" in name or "past_due" in name)
                and any(word in name for word in ("amount", "balance", "receivable", "value"))
            ):
                value_col = column
                break

    if value_col is None:
        raise ValueError(
            f"No supported value column found. Available columns: "
            f"{', '.join(map(str, df.columns))}"
        )

    values = numeric_series(df, value_col).dropna()
    if values.empty:
        return None

    if aggregation == "sum":
        return float(values.sum())
    return float(values.mean())


def prepare_data(metric_name, df):
    """Return one row per reporting month, or one current aggregate."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["period", "value"])

    period_col = find_period_column(metric_name, df)

    # Without a reporting-period column, calculate the current governed
    # aggregate but never manufacture a historical trend.
    if period_col is None:
        value = calculate_metric_value(metric_name, df)
        return pd.DataFrame([{"period": None, "value": value}])

    data = df.copy()
    data["_period"] = pd.to_datetime(
        data[period_col], errors="coerce"
    ).dt.to_period("M").astype("string")
    data = data.dropna(subset=["_period"])

    if data.empty:
        raise ValueError(
            f"'{period_col}' exists but contains no valid reporting dates."
        )

    rows = []
    for period, group in data.groupby("_period", sort=True):
        value = calculate_metric_value(metric_name, group)
        rows.append({"period": str(period), "value": value})

    return pd.DataFrame(rows).sort_values("period").reset_index(drop=True)


def find_target_period_column(targets):
    if targets is None or targets.empty:
        return None
    return choose_column(
        targets,
        ["month", "period", "month_start_date", "period_start_date",
         "period_end_date", "reporting_date"],
    )


def get_target(metric_name, targets, latest_period):
    if targets is None or targets.empty:
        return None

    target_col = choose_column(
        targets, TARGET_CANDIDATES.get(metric_name, [])
    )
    if target_col is None:
        return None

    target_rows = targets.copy()
    target_period_col = find_target_period_column(target_rows)

    if latest_period is not None and target_period_col is not None:
        target_months = pd.to_datetime(
            target_rows[target_period_col], errors="coerce"
        ).dt.to_period("M").astype("string")
        matched = target_rows.loc[target_months == str(latest_period)]
        if not matched.empty:
            target_rows = matched
        else:
            # Do not silently use a target from a different reporting month.
            return None

    values = pd.to_numeric(target_rows[target_col], errors="coerce").dropna()
    if values.empty:
        return None

    # Targets table can contain one row per department. MAX is used only
    # to retrieve the shared configured target, not to aggregate KPI values.
    target = float(values.max())

    # The current targets table stores rate targets as fractions for
    # attendance (0.94) and as percentage points for attrition/task
    # completion (1 and 80). Convert only fraction-style attendance values.
    if metric_name == "Attendance Rate" and 0 <= target <= 1:
        target *= 100

    return target


def format_value(value, unit):
    if value is None or pd.isna(value):
        return "Unavailable"
    value = float(value)
    if unit == "INR":
        return f"₹{value:,.2f}"
    if unit == "percent":
        return f"{value:.2f}%"
    return f"{value:,.0f}"


def get_status(value, target, direction):
    if value is None or pd.isna(value):
        return "⚪ Unavailable"

    if direction == "context":
        return "🔵 Informational"

    if target is None:
        return "⚪ Target not configured"

    if direction == "higher":
        if value >= target:
            return "🟢 On target"
        if value >= target * 0.95:
            return "🟡 Near target"
        return "🔴 Below target"

    if direction == "lower":
        if value <= target:
            return "🟢 On target"
        if value <= target * 1.05:
            return "🟡 Near target"
        return "🔴 Above target"

    return "⚪ Target not configured"


def trend_text(latest, previous, unit):
    if previous is None or pd.isna(previous):
        return "Unavailable — previous reporting period not available"

    change = float(latest) - float(previous)
    if unit == "percent":
        return f"{change:+.2f} percentage points vs previous period"
    if unit == "INR":
        return f"{change:+,.2f} vs previous period"
    return f"{change:+,.2f} vs previous period"


# ---------------------------------------------------------------------
# Load governed metric views and target table
# ---------------------------------------------------------------------
frames = {}
load_errors = {}

for metric_name, cfg in METRICS.items():
    try:
        frames[metric_name] = read_view(cfg["view"])
    except Exception as exc:
        load_errors[metric_name] = str(exc).splitlines()[0]

try:
    targets = read_target_table()
except Exception as exc:
    targets = pd.DataFrame()
    st.warning(
        "KPI target table could not be read: " + str(exc).splitlines()[0]
    )

if load_errors:
    with st.expander("Metric view diagnostics"):
        for metric_name, error in load_errors.items():
            st.error(f"{metric_name}: {error}")

if not frames:
    st.error("No governed metric views could be loaded. Check database connection and view permissions.")
    st.stop()

# ---------------------------------------------------------------------
# Step 4 - Month Selector
# The selector is based on months actually present in the governed views.
# It does not create missing periods or fabricate values.
# ---------------------------------------------------------------------
metric_names = list(METRICS.keys())
prepared_frames = {}
preparation_errors = {}

for metric_name in metric_names:
    if metric_name not in frames:
        continue
    try:
        prepared_frames[metric_name] = prepare_data(metric_name, frames[metric_name])
    except Exception as exc:
        preparation_errors[metric_name] = str(exc).splitlines()[0]

# The six period-based operating/financial KPIs define the selectable
# reporting months. Snapshot-only KPIs are deliberately not allowed to
# introduce a month that has no corresponding history in the core scorecard.
CORE_PERIOD_METRICS = [
    "Headcount",
    "Attrition Rate",
    "Payroll Cost",
    "Attendance Rate",
    "Net Profit",
    "Operating Margin",
]

period_sets = []
all_periods = set()
for metric_name in CORE_PERIOD_METRICS:
    prepared = prepared_frames.get(metric_name)
    if prepared is None or prepared.empty:
        continue
    periods = {
        str(value)
        for value in prepared["period"].dropna().tolist()
        if str(value).strip()
    }
    if periods:
        period_sets.append(periods)
        all_periods.update(periods)

common_periods = set.intersection(*period_sets) if period_sets else set()
month_options = sorted(common_periods or all_periods)

st.subheader("Executive KPI Scorecard")
if month_options:
    default_month = month_options[-1]
    selected_month = st.selectbox(
        "Select reporting month",
        options=month_options,
        index=month_options.index(default_month),
        format_func=lambda value: pd.Period(value, freq="M").strftime("%B %Y"),
        key="executive_scorecard_month_selector",
        help="Changing the month updates values, targets and month-over-month trends where the governed metric view exposes a reporting month.",
    )
    previous_month = str(pd.Period(selected_month, freq="M") - 1)
    st.caption(
        f"Selected month: {pd.Period(selected_month, freq='M').strftime('%B %Y')} "
        f"| Trend comparison: {pd.Period(previous_month, freq='M').strftime('%B %Y')}"
    )
else:
    selected_month = None
    previous_month = None
    st.warning("No reporting months could be identified in the core governed metric views. Month selection is unavailable.")


def value_for_month(metric_name, month):
    """Return the governed KPI value for one exact month; never use a nearby month."""
    prepared = prepared_frames.get(metric_name)
    if prepared is None or prepared.empty:
        return None
    period_rows = prepared.loc[prepared["period"].astype("string") == str(month)]
    if period_rows.empty:
        return None
    values = pd.to_numeric(period_rows["value"], errors="coerce").dropna()
    return float(values.iloc[-1]) if not values.empty else None


for start in range(0, len(metric_names), 4):
    columns = st.columns(4)
    for column, name in zip(columns, metric_names[start:start + 4]):
        with column:
            with st.container(border=True):
                cfg = METRICS[name]
                st.markdown(f"**{name}**")

                if name not in frames or name in preparation_errors:
                    st.metric("Selected-month value", "Unavailable")
                    st.caption("Target: Unavailable")
                    st.caption("Trend: Unavailable")
                    st.write("**Status:** ⚪ Unavailable")
                    if name in preparation_errors:
                        st.caption(f"Source issue: {preparation_errors[name]}")
                    detail_path, detail_label = KPI_DETAIL_PAGES[name]
                    st.page_link(detail_path, label=detail_label)
                    continue

                try:
                    prepared = prepared_frames[name]
                    has_period = (
                        not prepared.empty
                        and prepared["period"].notna().any()
                    )

                    if has_period and selected_month is not None:
                        current_value = value_for_month(name, selected_month)
                        previous_value = value_for_month(name, previous_month)
                        target_period = selected_month
                        value_caption = "Selected-month value"
                    else:
                        # The governed view has no month grain. Show its
                        # current aggregate honestly, without pretending it
                        # changes with the month selector or has a trend.
                        valid_values = pd.to_numeric(
                            prepared["value"], errors="coerce"
                        ).dropna()
                        current_value = (
                            float(valid_values.iloc[-1])
                            if not valid_values.empty else None
                        )
                        previous_value = None
                        target_period = selected_month
                        value_caption = "Current governed value (not month-grained)"

                    target = get_target(name, targets, target_period)

                    st.metric(
                        value_caption,
                        format_value(current_value, cfg["unit"]),
                    )
                    target_label = (
                        format_value(target, cfg["unit"])
                        if target is not None
                        else "Not configured for selected month"
                    )
                    st.caption(f"Target: {target_label}")

                    if has_period and selected_month is not None:
                        if previous_value is None:
                            trend_label = (
                                f"Unavailable — no governed value for {previous_month}"
                            )
                        elif current_value is None:
                            trend_label = (
                                f"Unavailable — no governed value for {selected_month}"
                            )
                        else:
                            trend_label = trend_text(
                                current_value, previous_value, cfg["unit"]
                            )
                    else:
                        trend_label = "Unavailable — governed view has no reporting month"

                    st.caption(f"Trend: {trend_label}")
                    st.write(
                        "**Status:** "
                        + get_status(current_value, target, cfg["direction"])
                    )

                    if not has_period:
                        st.caption(
                            "This KPI is a current aggregate from its governed view; "
                            "the source does not expose a reporting-period column, "
                            "so its value cannot be filtered by the month selector."
                        )
                    elif current_value is None:
                        st.caption(
                            "No value exists for the selected month in this governed view. "
                            "No value from another month is substituted."
                        )

                except Exception as exc:
                    st.metric("Selected-month value", "Unavailable")
                    st.caption("Target: Unavailable")
                    st.caption("Trend: Unavailable")
                    st.write("**Status:** ⚪ Unavailable")
                    st.error(f"{name}: {str(exc).splitlines()[0]}")

                detail_path, detail_label = KPI_DETAIL_PAGES[name]
                st.page_link(detail_path, label=detail_label)

st.divider()
st.caption(
    "Traffic-light rules: Green = target met; Yellow = within 5% of target; "
    "Red = target missed. Context-only KPIs are informational. Targets are "
    "read from metric_kpi_targets for the selected month and are never invented. "
    "Trends compare the selected month with the immediately previous calendar month. "
    "KPIs whose governed views do not expose a reporting month are shown as "
    "current aggregates and are explicitly marked as not month-grained."
)

# ---------------------------------------------------------------------
# Step 4 source-coverage check for the selected reporting month
# ---------------------------------------------------------------------
with st.expander("Step 4 month-selector coverage"):
    coverage_rows = []
    for name in metric_names:
        cfg = METRICS[name]
        prepared = prepared_frames.get(name)
        if name not in frames or prepared is None:
            coverage_rows.append({
                "KPI": name,
                "Selected-month value": "Unavailable",
                "Target": "Unavailable",
                "Previous-month trend": "Unavailable",
                "Month filtering": "Source unavailable",
            })
            continue

        has_period = not prepared.empty and prepared["period"].notna().any()
        if has_period and selected_month is not None:
            current_value = value_for_month(name, selected_month)
            previous_value = value_for_month(name, previous_month)
            target = get_target(name, targets, selected_month)
            month_filtering = "Supported by source"
            trend_status = (
                "Available" if current_value is not None and previous_value is not None
                else "Previous/current month missing from view"
            )
        else:
            values = pd.to_numeric(prepared["value"], errors="coerce").dropna()
            current_value = float(values.iloc[-1]) if not values.empty else None
            target = get_target(name, targets, selected_month)
            month_filtering = "Not supported — no period column"
            trend_status = "Not available from view"

        coverage_rows.append({
            "KPI": name,
            "Selected-month value": "Available" if current_value is not None else "Missing for selected month",
            "Target": "Configured" if target is not None else "Not configured",
            "Previous-month trend": trend_status,
            "Month filtering": month_filtering,
        })

    coverage = pd.DataFrame(coverage_rows)
    st.dataframe(coverage, use_container_width=True, hide_index=True)
    st.info(
        "Month selector is implemented. Any KPI without a reporting-period "
        "column in its governed metric view cannot be filtered historically; "
        "that source limitation is displayed rather than hidden."
    )
