-- Grain: one row per (test, day) where the test has at least one pair in that day's window.
--
-- Rolling 30-day flip rate: for each day, take the test's consecutive-execution pairs whose
-- two executions both fall in the 30 days ending at the end of that day, and divide the
-- pairs that flipped (pass to fail, or fail to pass) by all those pairs.
-- Example: in the window the test ran P, P, F, P: 2 flips out of 3 pairs = 0.667.

with days as (
    select
        date_key,
        calendar_date,
        calendar_date::timestamp + interval 1 day as window_end_utc  -- end of that day
    from {{ ref('dim_date') }}
),

pairs_in_window as (
    select
        d.date_key,
        d.calendar_date,
        p.test_key,
        p.is_flip
    from days as d
    join {{ ref('int_test_outcome_pairs') }} as p
        on p.previous_executed_at_utc >= d.window_end_utc - to_days({{ var('flip_window_days') }})
        and p.executed_at_utc < d.window_end_utc
)

select
    test_key,
    date_key,
    calendar_date,
    count(*)                                            as pairs_in_window,
    count(*) filter (where is_flip)                     as flips_in_window,
    count(*) filter (where is_flip) / count(*)          as flip_rate
from pairs_in_window
group by test_key, date_key, calendar_date
