# Task 3 — Dashboard Style Guide

## Dashboard
Headcount & Departments

## Visual style
- Background: White
- Primary text: Dark navy (#17324D)
- Positive/neutral series: Blue (#2878B5)
- Comparison series: Orange (#E69F00)
- Alert series: Vermillion (#D55E00)
- Use labels and symbols as well as colour; do not rely on colour alone.

## Typography
- Titles: Clear, sentence case
- KPI values: Large, with units
- Chart labels: Readable on laptop screens
- Dates: YYYY-MM
- Percentages: One decimal place
- Employee counts: Whole numbers with thousands separators

## Layout
1. Header: Headcount & Departments
2. Top row: Current headcount, monthly hires, monthly leavers, department count
3. Main charts: Headcount trend and department split
4. Supporting charts: Tenure bands and role mix
5. Joiners vs leavers comparison
6. Filters: Department and date range

## Chart rule
Every chart must have a descriptive title and a one-line takeaway calculated from the actual warehouse data.

## Review checklist
- Check readability at laptop and phone widths.
- Use consistent units and date formats.
- Verify KPI values against PostgreSQL.
- Label missing or unavailable metrics rather than inventing values.
