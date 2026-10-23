-- Governed metric catalog view.
-- Assumes the 28-row dictionary has been loaded as public.metric_dictionary.
-- Adjust column names here only if the loaded table uses different names.
CREATE OR REPLACE VIEW public.metric_catalog AS
SELECT
    metric_id,
    metric_name,
    business_definition,
    formula,
    source_table,
    grain,
    time_period,
    owner_team AS owner,
    unit,
    good_direction,
    caveat,
    minimum_group_size
FROM public.metric_dictionary;
