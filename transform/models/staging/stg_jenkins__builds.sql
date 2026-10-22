-- Grain: one row per Jenkins build (job_name, build_number).
-- Cleaned names and units; nothing is filtered out.

select
    job_name,
    build_number,
    result                          as build_result,
    started_at_utc                  as started_at_real_utc,
    duration_ms / 1000.0            as build_duration_s,
    commit_sha,
    build_url
from {{ source('raw', 'jenkins_builds') }}
