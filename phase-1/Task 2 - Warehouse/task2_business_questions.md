# PulseIQ Analytics — Task 2 Business Questions

1. **Department cost:** What are monthly gross pay, net pay, and employer payroll cost by department, and how do they compare with budget?
2. **Headcount trend:** How did department headcount change month by month, including hires, exits, and transfers?
3. **Attendance:** What are monthly attendance rates, scheduled days, present days, unpaid absences, and late arrivals by department?
4. **Attrition:** Which departments have the highest monthly exits and attrition rates, and how does actual attrition compare with targets?
5. **Invoices and cash collection:** What are monthly invoice amounts, paid amounts, and outstanding receivables by client?

## Fact table grain

- `fact_payroll`: one row per source payroll item (`payroll_item_id`).
- `fact_attendance_monthly`: one row per employee per monthly attendance period (`attendance_fact_id`). The source is monthly, not daily.
- `fact_leave`: one row per leave request (`leave_request_id`).
- `fact_headcount_monthly`: one row per department per date (`date_key`, `department_id`).

## Slowly changing employee dimension

`dim_employee` stores one row per employee history version. `employee_key` is the version-specific primary key; `employee_id` may repeat across history. Facts join using `employee_key`. Source department and role fields are preserved in each fact's JSONB `attributes` when not modeled as dedicated columns, so historical reporting can use the source-time department instead of silently assigning all history to the employee's current department.
