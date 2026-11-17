from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# PulseIQ | Task 15 - Executive Scorecard
# Cloud version: reads privacy-safe Parquet exports only.
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Executive Scorecard",
    page_icon="📊",
    layout="wide",
)

# A4 landscape print layout retained from the original dashboard.
st.markdown(
    """
    <style>
    @media print {
        @page { size: A4 landscape; margin: 8mm; }
        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stMain"], .main {
            width: 100% !important; min-width: 0 !important;
            background: #ffffff !important; color: #111111 !important;
            overflow: visible !important;
        }
        [data-testid="stSidebar"], header, footer,
        [data-testid="stToolbar"], [data-testid="stStatusWidget"],
        [data-testid="stExpander"] { display: none !important; }
        .block-container {
            max-width: 100% !important; width: 100% !important;
            padding: 0 !important; margin: 0 !important;
        }
        h1 { font-size: 20pt !important; color: #111111 !important; }
        h2 { font-size: 13pt !important; color: #111111 !important; }
        p, label, [data-testid="stCaptionContainer"] {
            font-size: 8pt !important; color: #333333 !important;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important; flex-wrap: nowrap !important;
            gap: 3mm !important; align-items: stretch !important;
            break-inside: avoid !important;
        }
        [data-testid="column"] {
            min-width: 0 !important; width: 25% !important;
            flex: 1 1 25% !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #aeb6bf !important; border-radius: 2mm !important;
            padding: 2mm !important; margin-bottom: 2mm !important;
            background: #ffffff !important; color: #111111 !important;
            break-inside: avoid !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 17pt !important; color: #111111 !important;
        }
        [data-testid="stMarkdownContainer"] { color: #111111 !important; }
        hr { margin: 2mm 0 !important; }
        * {
            box-shadow: none !important; text-shadow: none !important;
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
st.info("KPI values are sourced from privacy-safe exports of governed metric views.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "cloud_data_parquet"


@st.cache_data(ttl=300)
def load_parquet(dataset_name):
    allowed = {
        "metric_m01_headcount",
        "metric_m04_attrition_rate",
        "metric_m09_payroll_cost",
        "metric_m13_attendance_rate",
        "metric_m17_net_profit",
        "metric_m18_operating_margin",
        "metric_m22_task_completion_rate",
        "metric_kpi_targets",
        "cloud_overdue_summary",
    }
    if dataset_name not in allowed:
        raise ValueError("Dataset is not approved for the Executive Scorecard.")
    path = DATA_DIR / f"{dataset_name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Required cloud dataset not found: {path.name}")
    return pd.read_parquet(path)


METRICS = {
    "Headcount": {
        "dataset": "metric_m01_headcount", "date": "month_start_date",
        "value": "headcount", "aggregation": "sum", "unit": "count",
        "direction": "context",
    },
    "Attrition Rate": {
        "dataset": "metric_m04_attrition_rate", "date": "month_start_date",
        "value": "attrition_rate_pct", "aggregation": "mean", "unit": "percent",
        "direction": "lower",
    },
    "Payroll Cost": {
        "dataset": "metric_m09_payroll_cost", "date": "period_end_date",
        "value": "employer_cost", "aggregation": "sum", "unit": "INR",
        "direction": "lower",
    },
    "Attendance Rate": {
        "dataset": "metric_m13_attendance_rate", "date": "period_end_date",
        "value": "attendance_rate_pct", "aggregation": "mean", "unit": "percent",
        "direction": "higher",
    },
    "Net Profit": {
        "dataset": "metric_m17_net_profit", "date": "posting_period",
        "value": "net_profit", "aggregation": "sum", "unit": "INR",
        "direction": "higher",
    },
    "Operating Margin": {
        "dataset": "metric_m18_operating_margin", "date": "posting_period",
        "value": "operating_margin_pct", "aggregation": "weighted_ratio",
        "unit": "percent", "direction": "higher",
    },
    "Overdue Receivables": {
        "dataset": "cloud_overdue_summary", "date": None,
        "value": "total_overdue_amount", "aggregation": "sum",
        "unit": "INR", "direction": "lower",
    },
    "Task Completion Rate": {
        "dataset": "metric_m22_task_completion_rate", "date": None,
        "value": "completion_rate_pct", "aggregation": "weighted_ratio",
        "unit": "percent", "direction": "higher",
    },
}

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

TARGET_COLUMNS = {
    "Attrition Rate": "attrition_monthly_target_pct",
    "Attendance Rate": "attendance_rate_target",
    "Task Completion Rate": "task_completion_target_pct",
}


def to_month(series):
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").astype("string")


def aggregate_monthly(metric_name, df):
    cfg = METRICS[metric_name]
    if df.empty:
        return pd.DataFrame(columns=["period", "value"])

    work = df.copy()
    required = [cfg["date"], cfg["value"]]
    missing = [c for c in required if c not in work.columns]
    if missing:
        raise ValueError(f"{cfg['dataset']} is missing columns: {', '.join(missing)}")

    work["period"] = to_month(work[cfg["date"]])
    work[cfg["value"]] = pd.to_numeric(work[cfg["value"]], errors="coerce")
    work = work.dropna(subset=["period", cfg["value"]])

    if cfg["aggregation"] == "sum":
        result = work.groupby("period", as_index=False)[cfg["value"]].sum()
    elif cfg["aggregation"] == "mean":
        result = work.groupby("period", as_index=False)[cfg["value"]].mean()
    elif metric_name == "Operating Margin":
        if not {"revenue", "net_profit"}.issubset(work.columns):
            raise ValueError("Operating Margin export needs revenue and net_profit.")
        work["revenue"] = pd.to_numeric(work["revenue"], errors="coerce")
        work["net_profit"] = pd.to_numeric(work["net_profit"], errors="coerce")
        result = work.groupby("period", as_index=False).agg(
            revenue=("revenue", "sum"), net_profit=("net_profit", "sum")
        )
        result["value"] = (
            result["net_profit"] / result["revenue"].replace(0, pd.NA) * 100
        )
    else:
        raise ValueError(f"Unsupported aggregation for {metric_name}")

    if "value" not in result.columns:
        result = result.rename(columns={cfg["value"]: "value"})
    return result[["period", "value"]].sort_values("period").reset_index(drop=True)


def calculate_snapshot(metric_name, df):
    cfg = METRICS[metric_name]
    if df.empty:
        return None
    if metric_name == "Task Completion Rate":
        needed = {"completed_tasks", "total_tasks"}
        if not needed.issubset(df.columns):
            raise ValueError("Task completion export needs completed_tasks and total_tasks.")
        completed = pd.to_numeric(df["completed_tasks"], errors="coerce").sum()
        total = pd.to_numeric(df["total_tasks"], errors="coerce").sum()
        return float(completed / total * 100) if total > 0 else None

    if cfg["value"] not in df.columns:
        raise ValueError(f"{cfg['dataset']} is missing {cfg['value']}.")
    values = pd.to_numeric(df[cfg["value"]], errors="coerce").dropna()
    return float(values.sum()) if not values.empty else None


def get_target(metric_name, targets, selected_month):
    target_col = TARGET_COLUMNS.get(metric_name)
    if not target_col or targets.empty or target_col not in targets.columns:
        return None
    if "month" not in targets.columns:
        return None

    target_rows = targets.copy()
    target_rows["_month"] = to_month(target_rows["month"])
    target_rows = target_rows[target_rows["_month"] == str(selected_month)]
    values = pd.to_numeric(target_rows[target_col], errors="coerce").dropna()
    if values.empty:
        return None
    target = float(values.max())

    # Attendance targets are stored as fractions (e.g. 0.94 = 94%).
    if metric_name == "Attendance Rate" and 0 <= target <= 1:
        target *= 100
    return target


def format_value(value, unit):
    if value is None or pd.isna(value):
        return "Unavailable"
    if unit == "INR":
        return f"₹{float(value):,.2f}"
    if unit == "percent":
        return f"{float(value):.2f}%"
    return f"{float(value):,.0f}"


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


def trend_text(current, previous, unit):
    if previous is None or pd.isna(previous):
        return "Unavailable — previous reporting period not available"
    change = float(current) - float(previous)
    if unit == "percent":
        return f"{change:+.2f} percentage points vs previous period"
    if unit == "INR":
        return f"{change:+,.2f} vs previous period"
    return f"{change:+,.2f} vs previous period"


# Load only the datasets used by this scorecard.
raw_frames = {}
load_errors = {}
for name, cfg in METRICS.items():
    try:
        raw_frames[name] = load_parquet(cfg["dataset"])
    except Exception as exc:
        load_errors[name] = str(exc).splitlines()[0]

try:
    targets = load_parquet("metric_kpi_targets")
except Exception as exc:
    targets = pd.DataFrame()
    st.warning("KPI targets could not be loaded: " + str(exc).splitlines()[0])

prepared = {}
prep_errors = {}
for name in [
    "Headcount", "Attrition Rate", "Payroll Cost", "Attendance Rate",
    "Net Profit", "Operating Margin",
]:
    if name not in raw_frames:
        continue
    try:
        prepared[name] = aggregate_monthly(name, raw_frames[name])
    except Exception as exc:
        prep_errors[name] = str(exc).splitlines()[0]

# Core period-based metrics define the available month selector.
core = [
    "Headcount", "Attrition Rate", "Payroll Cost",
    "Attendance Rate", "Net Profit", "Operating Margin",
]
period_sets = []
all_periods = set()
for name in core:
    frame = prepared.get(name)
    if frame is not None and not frame.empty:
        periods = set(frame["period"].dropna().astype(str))
        if periods:
            period_sets.append(periods)
            all_periods.update(periods)

common_periods = set.intersection(*period_sets) if period_sets else set()
month_options = sorted(common_periods or all_periods)

st.subheader("Executive KPI Scorecard")
if month_options:
    selected_month = st.selectbox(
        "Select reporting month",
        options=month_options,
        index=len(month_options) - 1,
        format_func=lambda value: pd.Period(value, freq="M").strftime("%B %Y"),
        key="executive_scorecard_month_selector",
    )
    previous_month = str(pd.Period(selected_month, freq="M") - 1)
    st.caption(
        f"Selected month: {pd.Period(selected_month, freq='M').strftime('%B %Y')} "
        f"| Trend comparison: {pd.Period(previous_month, freq='M').strftime('%B %Y')}"
    )
else:
    selected_month = None
    previous_month = None
    st.warning("No reporting months are available in the exported core KPI datasets.")


def value_for_month(name, month):
    frame = prepared.get(name)
    if frame is None or frame.empty:
        return None
    rows = frame[frame["period"].astype(str) == str(month)]
    if rows.empty:
        return None
    values = pd.to_numeric(rows["value"], errors="coerce").dropna()
    return float(values.iloc[-1]) if not values.empty else None


metric_names = list(METRICS.keys())
for start in range(0, len(metric_names), 4):
    columns = st.columns(4)
    for column, name in zip(columns, metric_names[start:start + 4]):
        with column:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                cfg = METRICS[name]

                if name in load_errors:
                    current_value = None
                    st.caption(f"Source issue: {load_errors[name]}")
                    has_period = False
                elif name in prep_errors:
                    current_value = None
                    st.caption(f"Source issue: {prep_errors[name]}")
                    has_period = False
                elif name in prepared:
                    has_period = True
                    current_value = (
                        value_for_month(name, selected_month)
                        if selected_month is not None else None
                    )
                else:
                    has_period = False
                    try:
                        current_value = calculate_snapshot(name, raw_frames[name])
                    except Exception as exc:
                        current_value = None
                        st.caption(f"Source issue: {str(exc).splitlines()[0]}")

                previous_value = (
                    value_for_month(name, previous_month)
                    if has_period and previous_month is not None else None
                )
                target = (
                    get_target(name, targets, selected_month)
                    if selected_month is not None else None
                )

                value_label = (
                    "Selected-month value" if has_period
                    else "Current governed value (not month-grained)"
                )
                st.metric(value_label, format_value(current_value, cfg["unit"]))
                st.caption(
                    "Target: " + (
                        format_value(target, cfg["unit"])
                        if target is not None else "Not configured for selected month"
                    )
                )

                if has_period:
                    if current_value is None:
                        trend = f"Unavailable — no value for {selected_month}"
                    else:
                        trend = trend_text(current_value, previous_value, cfg["unit"])
                else:
                    trend = "Unavailable — source has no reporting month"
                st.caption("Trend: " + trend)
                st.write("**Status:** " + get_status(current_value, target, cfg["direction"]))

                if not has_period:
                    st.caption(
                        "This KPI is a current aggregate. Its source does not expose "
                        "a reporting period, so it is not changed by the month selector."
                    )
                elif current_value is None:
                    st.caption(
                        "No value exists for the selected month. No value from another "
                        "month is substituted."
                    )

                detail_path, detail_label = KPI_DETAIL_PAGES[name]
                st.page_link(detail_path, label=detail_label)

st.divider()
st.caption(
    "Traffic-light rules: Green = target met; Yellow = within 5% of target; "
    "Red = target missed. Context-only KPIs are informational. Targets are "
    "read from metric_kpi_targets and are never invented. Trends compare the "
    "selected month with the immediately previous calendar month. KPIs without "
    "a reporting month are shown as current aggregates."
)

with st.expander("Step 4 month-selector coverage"):
    coverage_rows = []
    for name in metric_names:
        if name in load_errors or name in prep_errors:
            coverage_rows.append({
                "KPI": name, "Selected-month value": "Unavailable",
                "Target": "Unavailable", "Previous-month trend": "Unavailable",
                "Month filtering": "Source unavailable",
            })
            continue
        has_period = name in prepared
        if has_period and selected_month is not None:
            current = value_for_month(name, selected_month)
            previous = value_for_month(name, previous_month)
            target = get_target(name, targets, selected_month)
            month_filtering = "Supported by source"
            trend_status = (
                "Available" if current is not None and previous is not None
                else "Previous/current month missing from view"
            )
        else:
            current = calculate_snapshot(name, raw_frames[name])
            target = None
            month_filtering = "Not supported — no period column"
            trend_status = "Not available from source"
        coverage_rows.append({
            "KPI": name,
            "Selected-month value": "Available" if current is not None else "Missing for selected month",
            "Target": "Configured" if target is not None else "Not configured",
            "Previous-month trend": trend_status,
            "Month filtering": month_filtering,
        })
    st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True, hide_index=True)
    st.info(
        "Month selection uses reporting periods present in the exported governed "
        "views. Snapshot KPIs remain current aggregates where the source has no month grain."
    )

if load_errors:
    with st.expander("Dataset loading diagnostics"):
        for name, error in load_errors.items():
            st.error(f"{name}: {error}")
