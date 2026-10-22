-- Grain: one row per test, identified by (suite_name, class_name, test_name).
-- The designed_* columns come from the demo answer key and are empty for real tests.

with executions as (
    select e.suite_name, e.class_name, e.test_name, t.started_at_utc
    from {{ ref('stg_jenkins__test_executions') }} as e
    join {{ ref('int_build_times') }} as t using (job_name, build_number)
),

tests as (
    select
        suite_name,
        class_name,
        test_name,
        min(started_at_utc) as first_seen_at_utc,
        max(started_at_utc) as last_seen_at_utc
    from executions
    group by suite_name, class_name, test_name
)

select
    {{ surrogate_key(['t.suite_name', 't.class_name', 't.test_name']) }} as test_key,
    t.suite_name,
    t.class_name,
    t.test_name,
    t.suite_name = 'demo'                     as is_demo,
    k.designed_as,
    k.cause                                   as designed_cause,
    k.designed_fail_rate,
    k.baseline_s                              as designed_baseline_s,
    k.slowed_s                                as designed_slowed_s,
    c.commit_sha                              as designed_slowdown_commit_sha,
    t.first_seen_at_utc,
    t.last_seen_at_utc
from tests as t
left join {{ ref('demo_expected_tests') }} as k
    using (suite_name, class_name, test_name)
left join {{ ref('demo_commits') }} as c
    on c.subject = k.slows_down_at_commit_subject
