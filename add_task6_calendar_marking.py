from pathlib import Path
p = Path(r"Task 5 - First Dashboard\pages\2_Attendance_Trends.py")
s = p.read_text(encoding="utf-8")

needle = "st.plotly_chart(fig, use_container_width=True)"
if needle not in s:
    raise SystemExit("Chart line not found. File unchanged.")

addition = '''
st.subheader("Holiday & Long-weekend calendar")
calendar_path = Path("Task 6 - Attendance and Leave Trends/task6_holiday_long_weekend_summary.csv")
if calendar_path.exists():
    calendar_df = pd.read_csv(calendar_path)
    visible_months = set(view["month"].astype(str).unique())
    calendar_view = calendar_df[
        calendar_df["year_month"].astype(str).isin(visible_months)
    ].copy()

    if not calendar_view.empty:
        calendar_view = calendar_view.rename(columns={
            "year_month": "Month",
            "attendance_rate_pct": "Attendance rate (%)",
            "calendar_working_days": "Calendar working days",
            "weekend_days": "Weekend days",
            "holidays": "Holidays",
            "holiday_long_weekend_candidates": "Holiday / long-weekend candidates",
            "calendar_coverage": "Calendar coverage"
        })
        st.dataframe(
            calendar_view[[
                "Month", "Attendance rate (%)", "Calendar working days",
                "Weekend days", "Holidays",
                "Holiday / long-weekend candidates", "Calendar coverage"
            ]],
            use_container_width=True,
            hide_index=True
        )
        st.caption(
            "Calendar context is shown for the months currently selected. "
            "A holiday or long-weekend candidate is context for interpreting "
            "attendance changes, not proof that it caused a dip."
        )
    else:
        st.info("No calendar rows match the selected attendance months.")
else:
    st.warning("Holiday calendar summary CSV was not found.")
'''

s = s.replace(needle, needle + "\n" + addition, 1)
p.write_text(s, encoding="utf-8")
print("Calendar context section added after the attendance chart.")
