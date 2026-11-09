
-- Identify payroll-related tables and their columns

SELECT
    table_name,
    ordinal_position,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      table_name ILIKE '%payroll%'
      OR table_name ILIKE '%salary%'
  )
ORDER BY table_name, ordinal_position;


-- Identify payroll-related views
SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
      table_name ILIKE '%payroll%'
      OR table_name ILIKE '%salary%'
  )
ORDER BY table_name;
