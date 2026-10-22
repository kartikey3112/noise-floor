-- Grain: one row per Jenkins build (job_name, build_number).
--
-- Simulated build times (decisions D-009 and D-032). Every demo build ran on one day, so a
-- 30-day window would hold everything. To show the window working, each build gets a
-- simulated start time: the newest build keeps its real time, and every earlier build is placed
-- a fixed number of hours (var simulated_build_spacing_hours) before the next one.
--
-- Example with 18 hours: the newest build at 2026-10-22 13:40 stays there, the one before it
-- becomes 2026-10-21 19:40, the one before that 2026-10-21 01:40, and so on.
-- The real time is kept next to it, and is_time_simulated says which one the metrics use.

with ordered as (
    select
        job_name,
        build_number,
        started_at_real_utc,
        row_number() over (
            partition by job_name order by started_at_real_utc desc, build_number desc
        ) - 1 as builds_before_newest,
        max(started_at_real_utc) over (partition by job_name) as newest_real_utc
    from {{ ref('stg_jenkins__builds') }}
)

select
    job_name,
    build_number,
    started_at_real_utc,
    newest_real_utc
        - to_hours(builds_before_newest * {{ var('simulated_build_spacing_hours') }})
        as started_at_utc,
    true as is_time_simulated
from ordered
