
-- ============================================================
-- PULSEIQ ANALYTICS
-- TASK 2: ANALYTICS WAREHOUSE - STAR SCHEMA
-- PostgreSQL 16
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS warehouse;
SET search_path TO warehouse, public;

-- ------------------------------------------------------------
-- 1. DIMENSION TABLES
-- ------------------------------------------------------------

-- Employee dimension: one row per employee history version.
-- employee_key identifies a specific version.
-- employee_id may appear more than once across history.

CREATE TABLE IF NOT EXISTS dim_employee (
    employee_key BIGINT PRIMARY KEY,
    employee_id TEXT,
    hire_date DATE,
    exit_date DATE,
    department_id TEXT,
    role_id TEXT,
    valid_from DATE,
    valid_to DATE,
    is_current BOOLEAN,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_employee_validity
        CHECK (
            valid_to IS NULL
            OR valid_from IS NULL
            OR valid_to >= valid_from
        )
);

CREATE TABLE IF NOT EXISTS dim_department (
    department_id TEXT PRIMARY KEY,
    department_name TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS dim_role (
    role_id TEXT PRIMARY KEY,
    department_id TEXT,
    role_title TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key BIGINT PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE,
    year INTEGER,
    month_number INTEGER,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_date_month
        CHECK (month_number IS NULL OR month_number BETWEEN 1 AND 12)
);

CREATE TABLE IF NOT EXISTS dim_leave_type (
    leave_type_id TEXT PRIMARY KEY,
    leave_type_name TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- ------------------------------------------------------------
-- 2. UNKNOWN EMPLOYEE MEMBER
-- ------------------------------------------------------------
-- Source payroll includes employee_key = -1 for two records.
-- Preserve those source keys instead of deleting or guessing
-- the real employee. This warehouse member represents unknown.

INSERT INTO dim_employee (
    employee_key,
    employee_id,
    valid_from,
    is_current,
    attributes
)
VALUES (
    -1,
    'UNKNOWN',
    DATE '1900-01-01',
    TRUE,
    '{"description": "Unknown or unresolved source employee key"}'::jsonb
)
ON CONFLICT (employee_key) DO NOTHING;

-- ------------------------------------------------------------
-- 3. FACT TABLES
-- ------------------------------------------------------------

-- Grain: one source payroll item.
-- payroll_item_id is the source record identifier.

CREATE TABLE IF NOT EXISTS fact_payroll (
    payroll_item_id TEXT PRIMARY KEY,
    employee_id TEXT,
    employee_key BIGINT NOT NULL DEFAULT -1,
    date_key BIGINT,
    run_id TEXT,
    period_end_date DATE,
    gross_pay NUMERIC(14,2),
    net_pay NUMERIC(14,2),
    employer_cost NUMERIC(14,2),
    overtime_pay NUMERIC(14,2),
    overtime_hours NUMERIC(12,2),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_payroll_gross_nonnegative
        CHECK (gross_pay IS NULL OR gross_pay >= 0),
    CONSTRAINT chk_payroll_net_nonnegative
        CHECK (net_pay IS NULL OR net_pay >= 0),
    CONSTRAINT fk_payroll_employee
        FOREIGN KEY (employee_key)
        REFERENCES dim_employee(employee_key),
    CONSTRAINT fk_payroll_date
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key)
);

-- Grain: one employee's monthly attendance record.
-- The source is monthly, not daily.

CREATE TABLE IF NOT EXISTS fact_attendance_monthly (
    attendance_fact_id TEXT PRIMARY KEY,
    employee_id TEXT,
    employee_key BIGINT NOT NULL DEFAULT -1,
    period_end_date DATE,
    scheduled_days NUMERIC(10,2),
    present_days NUMERIC(10,2),
    unpaid_absence_days NUMERIC(10,2),
    late_arrivals INTEGER,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT fk_attendance_employee
        FOREIGN KEY (employee_key)
        REFERENCES dim_employee(employee_key)
);

-- Grain: one leave request.

CREATE TABLE IF NOT EXISTS fact_leave (
    leave_request_id TEXT PRIMARY KEY,
    employee_id TEXT,
    employee_key BIGINT NOT NULL DEFAULT -1,
    leave_type_id TEXT,
    start_date DATE,
    end_date DATE,
    status TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_leave_dates
        CHECK (
            start_date IS NULL
            OR end_date IS NULL
            OR end_date >= start_date
        ),
    CONSTRAINT fk_leave_employee
        FOREIGN KEY (employee_key)
        REFERENCES dim_employee(employee_key),
    CONSTRAINT fk_leave_type
        FOREIGN KEY (leave_type_id)
        REFERENCES dim_leave_type(leave_type_id)
);

-- Grain: one department's headcount snapshot for one date.

CREATE TABLE IF NOT EXISTS fact_headcount_monthly (
    date_key BIGINT NOT NULL,
    department_id TEXT NOT NULL,
    headcount_start INTEGER,
    headcount_end INTEGER,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (date_key, department_id),
    CONSTRAINT chk_headcount_start
        CHECK (headcount_start IS NULL OR headcount_start >= 0),
    CONSTRAINT chk_headcount_end
        CHECK (headcount_end IS NULL OR headcount_end >= 0),
    CONSTRAINT fk_headcount_date
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key),
    CONSTRAINT fk_headcount_department
        FOREIGN KEY (department_id)
        REFERENCES dim_department(department_id)
);

-- ------------------------------------------------------------
-- 4. INDEXES
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_employee_natural_id
    ON dim_employee(employee_id);

CREATE INDEX IF NOT EXISTS idx_employee_department
    ON dim_employee(department_id);

CREATE INDEX IF NOT EXISTS idx_employee_role
    ON dim_employee(role_id);

CREATE INDEX IF NOT EXISTS idx_employee_history_dates
    ON dim_employee(valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_role_department
    ON dim_role(department_id);

CREATE INDEX IF NOT EXISTS idx_payroll_employee
    ON fact_payroll(employee_key);

CREATE INDEX IF NOT EXISTS idx_payroll_period
    ON fact_payroll(period_end_date);

CREATE INDEX IF NOT EXISTS idx_payroll_date_key
    ON fact_payroll(date_key);

CREATE INDEX IF NOT EXISTS idx_attendance_employee
    ON fact_attendance_monthly(employee_key);

CREATE INDEX IF NOT EXISTS idx_attendance_period
    ON fact_attendance_monthly(period_end_date);

CREATE INDEX IF NOT EXISTS idx_leave_employee
    ON fact_leave(employee_key);

CREATE INDEX IF NOT EXISTS idx_leave_dates
    ON fact_leave(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_leave_type
    ON fact_leave(leave_type_id);

CREATE INDEX IF NOT EXISTS idx_headcount_department
    ON fact_headcount_monthly(department_id);

COMMIT;

-- End of Task 2 warehouse schema.
