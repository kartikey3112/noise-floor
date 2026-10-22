-- Grain: one row per test execution: one test case in one Jenkins build
-- (job_name, build_number, case_index).
--
-- commit_key sits on the fact directly, even though the build implies it: the flaky rule is
-- "same test, same commit, both pass and fail", so that question needs only one join.
-- test_run_seq counts each test's executions in time order (1 = its first), which makes
-- "consecutive executions" for the flip rate a simple comparison of neighbours.

with executions as (
    select
        e.*,
        b.commit_sha,
        t.started_at_utc,
        t.started_at_real_utc
    from {{ ref('stg_jenkins__test_executions') }} as e
    join {{ ref('stg_jenkins__builds') }} as b using (job_name, build_number)
    join {{ ref('int_build_times') }} as t using (job_name, build_number)
)

select
    {{ surrogate_key(['job_name', 'build_number', 'case_index']) }}  as execution_key,
    {{ surrogate_key(['suite_name', 'class_name', 'test_name']) }}   as test_key,
    {{ surrogate_key(['job_name', 'build_number']) }}                as build_key,
    {{ surrogate_key(['commit_sha']) }}                              as commit_key,
    cast(strftime(started_at_utc, '%Y%m%d') as integer)              as date_key,
    started_at_utc                                                   as executed_at_utc,
    started_at_real_utc                                              as executed_at_real_utc,
    jenkins_status,
    outcome,
    duration_s,
    error_message,
    row_number() over (
        partition by suite_name, class_name, test_name
        order by started_at_utc, build_number, case_index
    )                                                                as test_run_seq
from executions
