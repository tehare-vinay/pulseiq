import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv


# Load the .env file from "Task 5 - First Dashboard".
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(
    page_title="Task 8 | Team Productivity",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def get_connection():
    """Create a reusable PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("PGUSER", "pulseiq_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


def read_query(sql, params=None):
    """Run a read query and return its result as a DataFrame."""
    with get_connection().cursor() as cur:
        cur.execute(sql, params or ())
        columns = [description[0] for description in cur.description]
        rows = cur.fetchall()

    return pd.DataFrame(rows, columns=columns)


st.title("Team Productivity Dashboard")
st.caption("Task 8 | Team and sprint delivery overview")

st.info(
    "Cancelled-task rule: Cancelled tasks are excluded from velocity, "
    "cycle-time and on-time-delivery calculations. They are shown separately "
    "and are not treated as completed deliveries."
)

try:
    # Dimension tables
    teams = read_query(
        """
        SELECT team_id, team_name, active_members
        FROM public.dim_team
        ORDER BY team_name
        """
    )

    sprints = read_query(
        """
        SELECT sprint_id, sprint_name, working_days, start_date, end_date
        FROM public.dim_sprint
        ORDER BY start_date, sprint_id
        """
    )

    if teams.empty or sprints.empty:
        st.error("Team or sprint dimension data is missing.")
        st.stop()

    teams["team_id"] = teams["team_id"].astype(str)
    teams["active_members"] = pd.to_numeric(
        teams["active_members"], errors="coerce"
    )

    # Filters
    sprint_options = ["All sprints"] + sprints["sprint_id"].astype(str).tolist()
    selected_sprint = st.selectbox("Select sprint", sprint_options)

    team_options = teams["team_id"].tolist()
    selected_teams = st.multiselect(
        "Filter teams",
        options=team_options,
        default=team_options,
    )

    if not selected_teams:
        st.warning("Select at least one team to display results.")
        st.stop()

    # Governed metric views
    velocity = read_query(
        """
        SELECT team_id, sprint_id, completed_story_points
        FROM public.metric_m24_velocity
        """
    )

    cycle_time = read_query(
        """
        SELECT team_id, sprint_id, avg_cycle_time_days, completed_task_count
        FROM public.metric_m25_avg_cycle_time
        """
    )

    on_time = read_query(
        """
        SELECT
            team_id,
            sprint_id,
            on_time_tasks,
            completed_tasks,
            on_time_delivery_rate_pct
        FROM public.metric_m23_on_time_delivery_rate
        """
    )

    # Task-health metrics use the dedicated view, not the raw fact table.
    work = read_query(
        """
        SELECT
            team_id,
            sprint_id,
            cancelled_tasks,
            blocked_tasks,
            reopened_tasks,
            reopen_events
        FROM public.metric_m26_task_health
        """
    )

    # Standardise join/filter key types.
    for dataframe in [velocity, cycle_time, on_time, work]:
        dataframe["team_id"] = dataframe["team_id"].astype(str)
        dataframe["sprint_id"] = dataframe["sprint_id"].astype(str)

    def apply_filters(dataframe):
        result = dataframe[
            dataframe["team_id"].isin(selected_teams)
        ].copy()

        if selected_sprint != "All sprints":
            result = result[result["sprint_id"] == selected_sprint]

        return result

    velocity = apply_filters(velocity)
    cycle_time = apply_filters(cycle_time)
    on_time = apply_filters(on_time)
    work = apply_filters(work)

    # Convert metric columns to numeric values safely.
    velocity["completed_story_points"] = pd.to_numeric(
        velocity["completed_story_points"], errors="coerce"
    )

    cycle_time["avg_cycle_time_days"] = pd.to_numeric(
        cycle_time["avg_cycle_time_days"], errors="coerce"
    )
    cycle_time["completed_task_count"] = pd.to_numeric(
        cycle_time["completed_task_count"], errors="coerce"
    )

    on_time["on_time_tasks"] = pd.to_numeric(
        on_time["on_time_tasks"], errors="coerce"
    )
    on_time["completed_tasks"] = pd.to_numeric(
        on_time["completed_tasks"], errors="coerce"
    )

    for column in [
        "cancelled_tasks",
        "blocked_tasks",
        "reopened_tasks",
        "reopen_events",
    ]:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    # Aggregate velocity by team across the selected sprint(s).
    velocity_team = velocity.groupby("team_id", as_index=False).agg(
        completed_story_points=("completed_story_points", "sum")
    )

    # Existing metric view provides a mean per team-sprint.
    # This team-level figure is the mean of the available sprint averages,
    # not a task-weighted average.
    cycle_team = cycle_time.groupby("team_id", as_index=False).agg(
        avg_cycle_time_days=("avg_cycle_time_days", "mean"),
        completed_task_count=("completed_task_count", "sum"),
    )

    # Recompute overall on-time rate from summed eligible and on-time counts.
    on_time_team = on_time.groupby("team_id", as_index=False).agg(
        on_time_tasks=("on_time_tasks", "sum"),
        eligible_completed_tasks=("completed_tasks", "sum"),
    )

    denominator = on_time_team["eligible_completed_tasks"].where(
        on_time_team["eligible_completed_tasks"] != 0
    )
    on_time_team["on_time_delivery_rate_pct"] = (
        on_time_team["on_time_tasks"] / denominator * 100
    )

    work_team = work.groupby("team_id", as_index=False).agg(
        cancelled_tasks=("cancelled_tasks", "sum"),
        blocked_tasks=("blocked_tasks", "sum"),
        reopened_tasks=("reopened_tasks", "sum"),
        reopen_events=("reopen_events", "sum"),
    )

    # Combine team dimensions and metric summaries.
    summary = teams[teams["team_id"].isin(selected_teams)].copy()

    for metric_frame in [
        velocity_team,
        cycle_team,
        on_time_team,
        work_team,
    ]:
        summary = summary.merge(metric_frame, on="team_id", how="left")

    summary["team_label"] = (
        summary["team_name"] + " (" + summary["team_id"] + ")"
    )

    numeric_columns = [
        "completed_story_points",
        "avg_cycle_time_days",
        "on_time_delivery_rate_pct",
        "cancelled_tasks",
        "blocked_tasks",
        "reopened_tasks",
        "reopen_events",
    ]

    for column in numeric_columns:
        if column in summary.columns:
            summary[column] = pd.to_numeric(
                summary[column], errors="coerce"
            )

    # Keep missing metric values missing for rates/cycle time rather than
    # displaying them as genuine zero performance.
    for column in [
        "completed_story_points",
        "cancelled_tasks",
        "blocked_tasks",
        "reopened_tasks",
        "reopen_events",
    ]:
        summary[column] = summary[column].fillna(0)

    total_velocity = summary["completed_story_points"].sum()
    total_cancelled = summary["cancelled_tasks"].sum()
    total_blocked = summary["blocked_tasks"].sum()
    total_reopened = summary["reopened_tasks"].sum()
    total_reopen_events = summary["reopen_events"].sum()

    # KPI cards: keep reopened tasks and total reopen events separate because
    # one task may have been reopened more than once.
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Completed Story Points", f"{total_velocity:,.0f}")
    k2.metric("Cancelled Tasks", f"{total_cancelled:,.0f}")
    k3.metric("Blocked Tasks", f"{total_blocked:,.0f}")
    k4.metric("Tasks Reopened", f"{total_reopened:,.0f}")
    k5.metric("Reopen Events", f"{total_reopen_events:,.0f}")

    st.subheader("Delivery metrics by team")
    st.caption(
        "Velocity is completed story points from the governed velocity view. "
        "On-time rate is recomputed from eligible completed-task counts. "
        "Cycle time is the mean of available sprint-level averages and is "
        "not task-weighted when multiple sprints are selected."
    )

    display_columns = [
        "team_name",
        "team_id",
        "active_members",
        "completed_story_points",
        "avg_cycle_time_days",
        "on_time_delivery_rate_pct",
        "cancelled_tasks",
        "blocked_tasks",
        "reopened_tasks",
        "reopen_events",
    ]

    display_names = {
        "team_name": "Team",
        "team_id": "Team ID",
        "active_members": "Active members",
        "completed_story_points": "Completed story points",
        "avg_cycle_time_days": "Avg cycle time (days)",
        "on_time_delivery_rate_pct": "On-time delivery (%)",
        "cancelled_tasks": "Cancelled tasks",
        "blocked_tasks": "Blocked tasks",
        "reopened_tasks": "Reopened tasks",
        "reopen_events": "Reopen events",
    }

    st.dataframe(
        summary[display_columns].rename(columns=display_names),
        use_container_width=True,
        hide_index=True,
    )

    # Team comparison charts
    st.subheader("Team comparisons")

    chart_data = summary.sort_values(
        "completed_story_points", ascending=False
    )

    fig_velocity = px.bar(
        chart_data,
        x="team_label",
        y="completed_story_points",
        title="Velocity: completed story points",
        labels={
            "team_label": "Team",
            "completed_story_points": "Completed story points",
        },
    )
    fig_velocity.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_velocity, use_container_width=True)

    st.caption(
        f"Insight: selected teams completed {total_velocity:,.0f} story points. "
        "Compare velocity alongside active team size and sprint duration; "
        "higher raw velocity alone does not prove better team health."
    )

    cycle_chart_data = summary.dropna(
        subset=["avg_cycle_time_days"]
    ).sort_values("avg_cycle_time_days", ascending=False)

    fig_cycle = px.bar(
        cycle_chart_data,
        x="team_label",
        y="avg_cycle_time_days",
        title="Average cycle time",
        labels={
            "team_label": "Team",
            "avg_cycle_time_days": "Days",
        },
    )
    fig_cycle.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_cycle, use_container_width=True)

    if not cycle_chart_data.empty:
        slowest = cycle_chart_data.iloc[0]
        st.caption(
            f"Insight: {slowest['team_name']} has the highest displayed "
            f"average cycle time ({slowest['avg_cycle_time_days']:.2f} days) "
            "among the selected teams. Review work type and sprint context "
            "before interpreting this as a performance issue."
        )

    on_time_chart_data = summary.dropna(
        subset=["on_time_delivery_rate_pct"]
    ).sort_values("on_time_delivery_rate_pct", ascending=False)

    fig_ontime = px.bar(
        on_time_chart_data,
        x="team_label",
        y="on_time_delivery_rate_pct",
        title="On-time delivery rate",
        labels={
            "team_label": "Team",
            "on_time_delivery_rate_pct": "On-time delivery (%)",
        },
    )
    fig_ontime.update_layout(
        xaxis_tickangle=-35,
        yaxis_range=[0, 100],
    )
    st.plotly_chart(fig_ontime, use_container_width=True)

    if not on_time_chart_data.empty:
        lowest = on_time_chart_data.iloc[-1]
        st.caption(
            f"Insight: {lowest['team_name']} has the lowest displayed "
            f"on-time delivery rate ({lowest['on_time_delivery_rate_pct']:.2f}%) "
            "among the selected teams. Check eligible task counts before "
            "drawing conclusions."
        )

    # Blocked, cancelled and reopened work: display separately from delivery metrics.
    st.subheader("Cancelled, blocked and reopened work")
    st.caption(
        "Cancelled tasks are excluded from velocity, cycle-time and on-time "
        "delivery calculations. Blocked tasks are unfinished work, not completed "
        "delivery. A reopened task is counted once when reopened_count > 0; "
        "reopen events sum all reopen_count values and can be higher."
    )

    work_chart = summary[
        ["team_label", "cancelled_tasks", "blocked_tasks", "reopened_tasks"]
    ].melt(
        id_vars="team_label",
        var_name="work_type",
        value_name="task_count",
    )
    work_chart["work_type"] = work_chart["work_type"].map(
        {
            "cancelled_tasks": "Cancelled tasks",
            "blocked_tasks": "Blocked tasks",
            "reopened_tasks": "Reopened tasks",
        }
    )

    # Order teams by the combined blocked + reopened count so the risk signals
    # are easy to find, while still showing cancelled tasks separately.
    team_order = summary.assign(
        risk_work=summary["blocked_tasks"] + summary["reopened_tasks"]
    ).sort_values("risk_work", ascending=False)["team_label"].tolist()
    fig_work = px.bar(
        work_chart,
        x="team_label",
        y="task_count",
        color="work_type",
        barmode="group",
        category_orders={"team_label": team_order},
        title="Cancelled, blocked and reopened tasks by team",
        labels={
            "team_label": "Team",
            "task_count": "Task count",
            "work_type": "Work type",
        },
        color_discrete_map={
            "Cancelled tasks": "#7DB7E8",
            "Blocked tasks": "#E45756",
            "Reopened tasks": "#F2A65A",
        },
    )
    fig_work.update_layout(xaxis_tickangle=-35, legend_title_text="Work type")
    st.plotly_chart(fig_work, use_container_width=True)

    # Numeric findings; ties are reported rather than arbitrarily choosing one team.
    if not summary.empty:
        max_blocked = summary["blocked_tasks"].max()
        max_reopened = summary["reopened_tasks"].max()
        blocked_leaders = summary.loc[
            summary["blocked_tasks"] == max_blocked, "team_name"
        ].tolist()
        reopened_leaders = summary.loc[
            summary["reopened_tasks"] == max_reopened, "team_name"
        ].tolist()

        st.caption(
            f"Insight: highest blocked-work count is {max_blocked:.0f} in "
            f"{', '.join(blocked_leaders)} for the current selection."
        )
        st.caption(
            f"Insight: highest reopened-task count is {max_reopened:.0f} in "
            f"{', '.join(reopened_leaders)} for the current selection."
        )
        st.caption(
            f"Insight: the selected teams have {total_blocked:,.0f} blocked tasks, "
            f"{total_reopened:,.0f} reopened tasks, and {total_reopen_events:,.0f} "
            "total reopen events. Investigate blockers and repeated rework before "
            "using velocity alone to assess team health."
        )

    if selected_sprint == "All sprints":
        st.caption(
            "All-sprint totals are shown. Cycle-time team values average the "
            "available sprint-level averages; they are not task-weighted. "
            "Sprint lengths and team sizes can differ."
        )
    else:
        selected_sprint_row = sprints[
            sprints["sprint_id"].astype(str) == selected_sprint
        ]
        if not selected_sprint_row.empty:
            sprint_row = selected_sprint_row.iloc[0]
            st.caption(
                f"Selected sprint: {selected_sprint} | "
                f"Working days: {sprint_row['working_days']} | "
                f"Dates: {sprint_row['start_date']} to {sprint_row['end_date']}"
            )
        else:
            st.caption(f"Selected sprint: {selected_sprint}")

except Exception as exc:
    st.error(
        "Dashboard could not load. Check PostgreSQL connection settings "
        "and confirm that the required metric views are available."
    )
    st.exception(exc)
