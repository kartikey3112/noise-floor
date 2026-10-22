-- Grain: one row per Jenkins build (job_name, build_number).

select
    {{ surrogate_key(['b.job_name', 'b.build_number']) }}  as build_key,
    b.job_name,
    b.build_number,
    b.build_result,
    t.started_at_utc,
    b.started_at_real_utc,
    t.is_time_simulated,
    b.build_duration_s,
    {{ surrogate_key(['b.commit_sha']) }}                  as commit_key,
    b.build_url
from {{ ref('stg_jenkins__builds') }} as b
join {{ ref('int_build_times') }} as t using (job_name, build_number)
