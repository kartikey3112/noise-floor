-- Grain: one row per calendar day (UTC) from the first to the last simulated build day.
-- date_key is the date as a yyyymmdd number, e.g. 20261022.

with bounds as (
    select
        min(started_at_utc)::date as first_day,
        max(started_at_utc)::date as last_day
    from {{ ref('int_build_times') }}
),

days as (
    select unnest(generate_series(first_day, last_day, interval 1 day))::date as calendar_date
    from bounds
)

select
    cast(strftime(calendar_date, '%Y%m%d') as integer) as date_key,
    calendar_date,
    dayname(calendar_date)                              as day_name,
    isodow(calendar_date)                               as iso_day_of_week,
    weekofyear(calendar_date)                           as iso_week,
    isodow(calendar_date) in (6, 7)                     as is_weekend
from days
