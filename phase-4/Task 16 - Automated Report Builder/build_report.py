from pathlib import Path
from datetime import datetime
from calendar import monthrange
import os
import argparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)


# --------------------------------------------------
# Project configuration
# --------------------------------------------------

TASK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TASK_DIR.parents[1]

REPORT_DIR = TASK_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")


def env_value(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def get_connection():
    return psycopg2.connect(
        host=env_value("PULSEIQ_PGHOST", "PGHOST", default="localhost"),
        port=env_value("PULSEIQ_PGPORT", "PGPORT", default="5432"),
        dbname=env_value(
            "PULSEIQ_PGDATABASE", "PULSEIQ_DATABASE",
            "POSTGRES_DB"
        ),
        user=env_value(
            "PULSEIQ_PGUSER", "PULSEIQ_USER", "POSTGRES_USER"
        ),
        password=env_value(
            "PULSEIQ_PGPASSWORD", "PULSEIQ_PASSWORD",
            "POSTGRES_PASSWORD"
        )
    )


# --------------------------------------------------
# Fetch governed monthly metrics
# --------------------------------------------------

def fetch_report_data(month):

    month_start = datetime.strptime(month, "%Y-%m").date()
    month_end = (
        month_start.replace(day=28).replace(day=1)
    )

    if month_start.month == 12:
        from datetime import date
        month_end = date(month_start.year, 12, 31)
    else:
        from datetime import date
        next_month = date(
            month_start.year,
            month_start.month + 1,
            1
        )
        month_end = next_month - __import__("datetime").timedelta(days=1)

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cur:

            # Headcount by department
            cur.execute("""
                SELECT department_id,
                       SUM(headcount) AS headcount
                FROM public.metric_m01_headcount
                WHERE NULLIF(BTRIM(month_start_date), '')::date = %s
                GROUP BY department_id
                ORDER BY department_id
            """, (month_start,))

            headcount = cur.fetchall()

            # Monthly headcount trend: 12 months ending with the selected month
            cur.execute("""
                SELECT
                    NULLIF(BTRIM(month_start_date), '')::date AS month_start_date,
                    SUM(headcount) AS headcount
                FROM public.metric_m01_headcount
                WHERE NULLIF(BTRIM(month_start_date), '')::date
                      BETWEEN (%s::date - INTERVAL '11 months') AND %s::date
                GROUP BY NULLIF(BTRIM(month_start_date), '')::date
                ORDER BY month_start_date
            """, (month_start, month_start))

            headcount_trend = cur.fetchall()

            # Employer payroll cost by department
            cur.execute("""
                SELECT department_id,
                       SUM(employer_cost) AS employer_cost
                FROM public.metric_m09_payroll_cost
                WHERE NULLIF(BTRIM(period_end_date), '')::date = %s
                GROUP BY department_id
                ORDER BY department_id
            """, (month_end,))

            payroll = cur.fetchall()

            # Attendance rate by department
            cur.execute("""
                SELECT department_id,
                       AVG(attendance_rate_pct) AS attendance_rate_pct
                FROM public.metric_m13_attendance_rate
                WHERE NULLIF(BTRIM(period_end_date), '')::date = %s
                GROUP BY department_id
                ORDER BY department_id
            """, (month_end,))

            attendance = cur.fetchall()

            # Profit and Loss
            cur.execute("""
                SELECT month, operating_revenue, other_income,
                       total_revenue, total_expenses,
                       net_profit, net_profit_margin_pct
                FROM public.vw_task11_monthly_pnl
                WHERE BTRIM(month) = %s
            """, (month,))

            pnl = cur.fetchone()

            # Cash Flow
            cur.execute("""
                SELECT month, cash_in, cash_out, net_cash_flow
                FROM public.vw_task12_monthly_cash_flow
                WHERE month = %s::date
            """, (month_start,))

            cashflow = cur.fetchone()


        # Calculate actual data cut-off from governed monthly views
            cur.execute("""
                SELECT MAX(cutoff_date) AS data_cutoff
                FROM (
                    SELECT MAX(period_end_date)::date AS cutoff_date
                    FROM public.metric_m13_attendance_rate
                    WHERE NULLIF(BTRIM(period_end_date), '')::date
      BETWEEN %s AND %s

                    UNION ALL

                    SELECT (
                        MAX(to_date(month || '-01', 'YYYY-MM-DD'))
                        + INTERVAL '1 month - 1 day'
                    )::date AS cutoff_date
                    FROM public.vw_task11_monthly_pnl
                    WHERE month = %s

                    UNION ALL

                    SELECT (
                        date_trunc('month', MAX(month))
                        + INTERVAL '1 month - 1 day'
                    )::date AS cutoff_date
                    FROM public.vw_task12_monthly_cash_flow
                    WHERE month >= %s AND month <= %s
                ) AS source_dates
            """, (month_start, month_end, month, month_start, month_end))

            cutoff_row = cur.fetchone()
            data_cutoff = cutoff_row["data_cutoff"] if cutoff_row else None


            if not headcount:
                raise ValueError("No headcount data found for " + month)

            if not payroll:
                raise ValueError("No payroll data found for " + month)

            if not attendance:
                raise ValueError("No attendance data found for " + month)

            if pnl is None:
                raise ValueError("No P&L data found for " + month)

            if cashflow is None:
                raise ValueError("No cash flow data found for " + month)

            return {
                "headcount": headcount,
                "headcount_trend": headcount_trend,
                "payroll": payroll,
                "attendance": attendance,
                "pnl": pnl,
                "cashflow": cashflow,
                "data_cutoff": data_cutoff
            }

    finally:
        connection.close()


# --------------------------------------------------
# PDF formatting helpers
# --------------------------------------------------

def number(value):
    return f"{float(value or 0):,.2f}"


def create_table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#203864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#EDF2F8")]),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return table


# --------------------------------------------------
# Generate monthly PDF
# --------------------------------------------------

def generate_pdf(month, data):

    output_file = REPORT_DIR / (
        f"PulseIQ_Monthly_Report_{month}.pdf"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=21,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#203864"),
        spaceAfter=8
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#203864"),
        spaceBefore=12,
        spaceAfter=7
    )

    story = []

    story.append(Paragraph(
        "PulseIQ Analytics",
        title_style
    ))

    story.append(Paragraph(
        f"Monthly Business Performance Report | {month}",
        styles["Heading2"]
    ))

    story.append(Paragraph(
        "Generated on: " + datetime.now().strftime("%d %B %Y"),
        styles["Normal"]
    ))

    # Step 3: reporting date range and data cut-off
    report_start = datetime.strptime(month, "%Y-%m").date()
    report_end = report_start.replace(
        day=monthrange(report_start.year, report_start.month)[1]
    )

    story.append(Paragraph(
        f"<b>Reporting Date Range:</b> "
        f"{report_start:%d %B %Y} to {report_end:%d %B %Y}",
        styles["Normal"]
    ))
    cutoff_text = (
    data["data_cutoff"].strftime("%d %B %Y")
    if data["data_cutoff"]
    else "Not available"
)

    story.append(Paragraph(
        f"<b>Data Cut-off:</b> {cutoff_text}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 8 * mm))

    # KPI calculations
    total_headcount = sum(
        float(row["headcount"] or 0)
        for row in data["headcount"]
    )

    total_payroll = sum(
        float(row["employer_cost"] or 0)
        for row in data["payroll"]
    )

    attendance_values = [
        float(row["attendance_rate_pct"])
        for row in data["attendance"]
        if row["attendance_rate_pct"] is not None
    ]

    average_attendance = (
        sum(attendance_values) / len(attendance_values)
        if attendance_values else 0
    )

    pnl = data["pnl"]
    cash = data["cashflow"]

    story.append(Paragraph("1. Executive KPI Summary", heading_style))

    kpi_data = [
        ["Metric", "Monthly Value"],
        ["Total Headcount", f"{total_headcount:,.0f}"],
        ["Employer Payroll Cost", number(total_payroll)],
        ["Average Department Attendance", f"{average_attendance:.2f}%"],
        ["Total Revenue", number(pnl["total_revenue"])],
        ["Total Expenses", number(pnl["total_expenses"])],
        ["Net Profit", number(pnl["net_profit"])],
        ["Net Cash Flow", number(cash["net_cash_flow"])]
    ]

    story.append(create_table(
        kpi_data, [95 * mm, 75 * mm]
    ))

    # Department breakdown
    story.append(Paragraph(
        "2. Department-wise Performance",
        heading_style
    ))

    payroll_map = {
        row["department_id"]: row["employer_cost"]
        for row in data["payroll"]
    }

    attendance_map = {
        row["department_id"]: row["attendance_rate_pct"]
        for row in data["attendance"]
    }

    department_data = [[
        "Department",
        "Headcount",
        "Employer Cost",
        "Attendance %"
    ]]

    for row in data["headcount"]:
        dept = row["department_id"]

        department_data.append([
            str(dept),
            f'{float(row["headcount"] or 0):,.0f}',
            number(payroll_map.get(dept)),
            (
                f'{float(attendance_map[dept]):.2f}%'
                if attendance_map.get(dept) is not None
                else "N/A"
            )
        ])

    story.append(create_table(
        department_data,
        [35 * mm, 35 * mm, 50 * mm, 50 * mm]
    ))

    # P&L section
    story.append(Paragraph(
        "3. Profit and Loss Summary",
        heading_style
    ))

    pnl_data = [
        ["Metric", "Value"],
        ["Operating Revenue", number(pnl["operating_revenue"])],
        ["Other Income", number(pnl["other_income"])],
        ["Total Revenue", number(pnl["total_revenue"])],
        ["Total Expenses", number(pnl["total_expenses"])],
        ["Net Profit", number(pnl["net_profit"])],
        ["Net Profit Margin", f'{float(pnl["net_profit_margin_pct"] or 0):.2f}%']
    ]

    story.append(create_table(
        pnl_data, [95 * mm, 75 * mm]
    ))

    # Cash flow section
    cash_data = [
    ["Metric", "Value"],
    ["Cash In", number(cash["cash_in"])],
    ["Cash Out", number(cash["cash_out"])],
    ["Net Cash Flow", number(cash["net_cash_flow"])]
    ]

    story.append(KeepTogether([
    Paragraph("4. Cash Flow Summary", heading_style),
    create_table(cash_data, [95 * mm, 75 * mm])
    ]))

    # Monthly headcount trend chart (up to and including the selected month)
    story.append(Paragraph(
        "5. Monthly Headcount Trend",
        heading_style
    ))

    trend_rows = data["headcount_trend"]
    if trend_rows:
        trend_labels = [
            row["month_start_date"].strftime("%b %Y")
            if hasattr(row["month_start_date"], "strftime")
            else str(row["month_start_date"])
            for row in trend_rows
        ]
        trend_values = [
            float(row["headcount"] or 0)
            for row in trend_rows
        ]

        chart_drawing = Drawing(170 * mm, 75 * mm)
        chart = HorizontalLineChart()
        chart.x = 18
        chart.y = 18
        chart.width = 145 * mm
        chart.height = 52 * mm
        chart.data = [trend_values]
        chart.categoryAxis.categoryNames = trend_labels
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.angle = 0
        chart.valueAxis.valueMin = 0
        maximum = max(trend_values) if trend_values else 0
        chart.valueAxis.valueMax = max(1, maximum * 1.15)
        chart.valueAxis.valueStep = max(1, round(maximum / 5))
        chart.lines[0].strokeWidth = 2
        chart.lines[0].symbol = makeMarker("FilledCircle", size=4)
        chart_drawing.add(chart)
        story.append(chart_drawing)
    else:
        story.append(Paragraph(
            "No historical headcount trend data is available for this period.",
            styles["BodyText"]
        ))

    # Report notes
    story.append(Paragraph(
        "6. Reporting Notes",
        heading_style
    ))

    notes = [
        "This report uses existing governed PulseIQ metric views.",
        "Department-level metrics reflect the available privacy-filtered "
        "records in the source views.",
        "Average attendance is the simple average of available "
        "department attendance rates.",
        "Financial amounts are presented in the source currency.",
        "This report is an automated summary and should be reviewed "
        "before business decisions."
    ]

    for note in notes:
        story.append(Paragraph(
            "• " + note,
            styles["BodyText"]
        ))
        story.append(Spacer(1, 4))

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    doc.build(story)

    return output_file


# --------------------------------------------------
# Main execution
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="PulseIQ Monthly PDF Report Builder"
    )

    parser.add_argument(
        "--month",
        required=True,
        help="Reporting month in YYYY-MM format (example: 2026-09)"
    )

    args = parser.parse_args()

    try:
        parsed_month = datetime.strptime(args.month, "%Y-%m")
        if parsed_month.strftime("%Y-%m") != args.month:
            raise ValueError("Month must use YYYY-MM format, for example 2026-09")

        print(f"Building monthly report for {args.month}...")

        data = fetch_report_data(args.month)

        output = generate_pdf(args.month, data)

        print("Report generated successfully.")
        print(f"Output: {output}")

    except Exception as error:
        print(f"REPORT GENERATION FAILED: {error}")
        raise


if __name__ == "__main__":
    main()
