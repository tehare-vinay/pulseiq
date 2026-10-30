import os
import pandas as pd
import streamlit as st
import psycopg2
import plotly.express as px


st.set_page_config(
    page_title="Task 8 | Team Productivity",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("FGHOST", "localhost"),
        port=os.getenv("FGPORT", "5432"),
        dbname=os.getenv("FGDATABASE", "pulseiq_warehouse"),
        user=os.getenv("FGUSER", "pulseiq_user"),
        password=os.getenv("FGPASSWORD", ""),
        connect_timeout=5,
    )


def read_query(sql, params=None):
    with get_connection().cursor() as cur:
        cur.execute(sql, params or ())
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


st.title("Team Productivity Dashboard")
st.caption("Task 8 | Team and sprint delivery overview")

st.info(
    "Cancelled-task rule: Cancelled tasks are excluded from velocity, "
    "cycle time and on-time delivery calculations. They are displayed "
    "separately and are not treated as completed deliveries."
)

try:
    teams = read_query("""
        SELECT team_id, team_name, active_members
        FROM public.dim_team
        ORDER BY team_name
    """)

    sprints = read_query("""
        SELECT sprint_id, sprint_name, working_days, start_date, end_date
        FROM public.dim_sprint
        ORDER BY start_date, sprint_id
    """)

    if teams.empty or sprints.empty:
        st.error("Team or sprint dimension data is missing.")
        st.stop()

    sprint_options = ["All sprints"] + sprints["sprint_id"].astype(str).tolist()
    selected_sprint = st.selectbox("Select sprint", sprint_options)

    team_options = teams["team_id"].astype(str).tolist()
    selected_teams = st.multiselect(
        "Filter teams",
        options=team_options,
        default=team_options
    )

    if not selected_teams:
        st.warning("Select at least one team to display results.")
        st.stop()

    velocity = read_query("""
        SELECT team_id, sprint_id, completed_story_points
        FROM public.metric_m24_velocity
    """)

    cycle_time = read_query("""
        SELECT team_id, sprint_id, avg_cycle_time_days, completed_task_count
        FROM public.metric_m25_avg_cycle_time
    """)

    on_time = read_query("""
        SELECT team_id, sprint_id, on_time_tasks, completed_tasks,
               on_time_delivery_rate_pct
        FROM public.metric_m23_on_time_delivery_rate
    """)

    work = read_query("""
        SELECT
            team_id,
            sprint_id,
            COUNT(*) FILTER (WHERE TRIM(status) = 'Cancelled') AS cancelled_tasks,
            COUNT(*) FILTER (WHERE TRIM(status) = 'Blocked') AS blocked_tasks,
            COUNT(*) FILTER (
                WHERE COALESCE(NULLIF(TRIM(reopened_count), '')::numeric, 0) > 0
            ) AS reopened_tasks,
            COALESCE(
                SUM(COALESCE(NULLIF(TRIM(reopened_count), '')::numeric, 0)),
                0
            ) AS reopen_events
        FROM public.fact_task
        GROUP BY team_id, sprint_id
    """)

    for df in [velocity, cycle_time, on_time, work]:
        df["team_id"] = df["team_id"].astype(str)
        df["sprint_id"] = df["sprint_id"].astype(str)

    teams["team_id"] = teams["team_id"].astype(str)
    teams["active_members"] = pd.to_numeric(
        teams["active_members"], errors="coerce"
    )

    def apply_filters(df):
        result = df[df["team_id"].isin(selected_teams)].copy()
        if selected_sprint != "All sprints":
            result = result[result["sprint_id"] == selected_sprint]
        return result

    velocity = apply_filters(velocity)
    cycle_time = apply_filters(cycle_time)
    on_time = apply_filters(on_time)
    work = apply_filters(work)

    velocity["completed_story_points"] = pd.to_numeric(
        velocity["completed_story_points"], errors="coerce"
    )
    cycle_time["avg_cycle_time_days"] = pd.to_numeric(
        cycle_time["avg_cycle_time_days"], errors="coerce"
    )
    cycle_time["completed_task_count"] = pd.to_numeric(
        cycle_time["completed_task_count"], errors="coerce"
    )
    on_time["on_time_delivery_rate_pct"] = pd.to_numeric(
        on_time["on_time_delivery_rate_pct"], errors="coerce"
    )

    # Aggregate team-sprint metric rows for the selected filters.
    velocity_team = velocity.groupby("team_id", as_index=False)[
        "completed_story_points"
    ].sum(min_count=1)

    cycle_team = cycle_time.groupby("team_id", as_index=False).agg(
        avg_cycle_time_days=("avg_cycle_time_days", "mean"),
        completed_task_count=("completed_task_count", "sum")
    )

    on_time_team = on_time.groupby("team_id", as_index=False).agg(
        on_time_tasks=("on_time_tasks", "sum"),
        eligible_completed_tasks=("completed_tasks", "sum")
    )
    on_time_team["on_time_delivery_rate_pct"] = (
        pd.to_numeric(on_time_team["on_time_tasks"], errors="coerce")
        / pd.to_numeric(
            on_time_team["eligible_completed_tasks"], errors="coerce"
        ).replace(0, pd.NA)
        * 100
    )

    work_team = work.groupby("team_id", as_index=False).agg(
        cancelled_tasks=("cancelled_tasks", "sum"),
        blocked_tasks=("blocked_tasks", "sum"),
        reopened_tasks=("reopened_tasks", "sum"),
        reopen_events=("reopen_events", "sum")
    )

    summary = teams[teams["team_id"].isin(selected_teams)].copy()
    for df in [velocity_team, cycle_team, on_time_team, work_team]:
        summary = summary.merge(df, on="team_id", how="left")

    summary["team_label"] = summary["team_name"] + " (" + summary["team_id"] + ")"

    for col in [
        "completed_story_points", "avg_cycle_time_days",
        "on_time_delivery_rate_pct", "cancelled_tasks",
        "blocked_tasks", "reopened_tasks", "reopen_events"
    ]:
        if col in summary.columns:
            summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0)

    total_velocity = summary["completed_story_points"].sum()
    total_cancelled = summary["cancelled_tasks"].sum()
    total_blocked = summary["blocked_tasks"].sum()
    total_reopened = summary["reopened_tasks"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Completed Story Points", f"{total_velocity:,.0f}")
    k2.metric("Cancelled Tasks", f"{total_cancelled:,.0f}")
    k3.metric("Blocked Tasks", f"{total_blocked:,.0f}")
    k4.metric("Tasks Reopened", f"{total_reopened:,.0f}")

    st.subheader("Delivery metrics by team")
    st.caption(
        "Cycle time is the mean of the available team-sprint averages. "
        "On-time rate is recomputed from eligible completed tasks."
    )

    st.dataframe(
        summary[[
            "team_name", "team_id", "active_members",
            "completed_story_points", "avg_cycle_time_days",
            "on_time_delivery_rate_pct", "cancelled_tasks",
            "blocked_tasks", "reopened_tasks", "reopen_events"
        ]].rename(columns={
            "team_name": "Team",
            "team_id": "Team ID",
            "active_members": "Active members",
            "completed_story_points": "Completed story points",
            "avg_cycle_time_days": "Avg cycle time (days)",
            "on_time_delivery_rate_pct": "On-time delivery (%)",
            "cancelled_tasks": "Cancelled tasks",
            "blocked_tasks": "Blocked tasks",
            "reopened_tasks": "Reopened tasks",
            "reopen_events": "Reopen events"
        }),
        use_container_width=True,
        hide_index=True
    )

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
            "completed_story_points": "Completed story points"
        }
    )
    fig_velocity.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_velocity, use_container_width=True)

    st.caption(
        f"Insight: selected teams completed {total_velocity:,.0f} story points. "
        "Interpret velocity alongside team size and sprint duration."
    )

    fig_cycle = px.bar(
        summary.sort_values("avg_cycle_time_days", ascending=False),
        x="team_label",
        y="avg_cycle_time_days",
        title="Average cycle time",
        labels={
            "team_label": "Team",
            "avg_cycle_time_days": "Days"
        }
    )
    fig_cycle.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_cycle, use_container_width=True)

    fig_ontime = px.bar(
        summary.sort_values("on_time_delivery_rate_pct", ascending=False),
        x="team_label",
        y="on_time_delivery_rate_pct",
        title="On-time delivery rate",
        labels={
            "team_label": "Team",
            "on_time_delivery_rate_pct": "On-time delivery (%)"
        }
    )
    fig_ontime.update_layout(xaxis_tickangle=-35, yaxis_range=[0, 100])
    st.plotly_chart(fig_ontime, use_container_width=True)

    st.subheader("Cancelled, blocked and reopened work")
    st.caption(
        "Cancelled tasks are reported separately. Reopened tasks count each "
        "task with reopened_count greater than zero; reopen events are the sum "
        "of reopened_count. These measures are not interchangeable."
    )

    work_chart = summary[[
        "team_label", "cancelled_tasks", "blocked_tasks",
        "reopened_tasks"
    ]].melt(
        id_vars="team_label",
        var_name="work_type",
        value_name="task_count"
    )

    fig_work = px.bar(
        work_chart,
        x="team_label",
        y="task_count",
        color="work_type",
        barmode="group",
        title="Cancelled, blocked and reopened tasks",
        labels={
            "team_label": "Team",
            "task_count": "Tasks",
            "work_type": "Work type"
        }
    )
    fig_work.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_work, use_container_width=True)

    if selected_sprint == "All sprints":
        st.caption(
            "All-sprint totals are shown. Cycle-time team values average the "
            "available sprint-level averages; they are not task-weighted."
        )
    else:
        st.caption(f"Selected sprint: {selected_sprint}")

except Exception as exc:
    st.error(
        "Dashboard could not load. Check PostgreSQL connection settings "
        "and confirm that the metric views are available."
    )
    st.exception(exc)
