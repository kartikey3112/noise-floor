-- Grain: one row per test. The summary the report reads: is it flaky, how often does it flip
-- now, and has it slowed down.
-- "Now" means the 30-day window ending on the last day with builds.

with runs as (
    select
        test_key,
        count(*) filter (where outcome in ('pass', 'fail'))  as runs,
        count(*) filter (where outcome = 'fail')             as fails
    from {{ ref('fct_test_executions') }}
    group by test_key
),

divergence as (
    select
        test_key,
        count(*) filter (where is_divergent)                as divergent_commits,
        count(*)                                            as commits_run_on
    from {{ ref('mart_same_commit_divergence') }}
    group by test_key
),

latest_flip_rate as (
    select test_key, flip_rate, flips_in_window, pairs_in_window
    from {{ ref('mart_flip_rate_daily') }}
    where date_key = (select max(date_key) from {{ ref('dim_date') }})
),

regressions as (
    select
        test_key,
        count(*)                                            as regression_episodes,
        arg_min(onset_commit_key, onset_at_utc)             as first_regression_commit_key,
        min(onset_at_utc)                                   as first_regression_at_utc
    from {{ ref('mart_runtime_regressions') }}
    group by test_key
)

select
    t.test_key,
    t.suite_name,
    t.class_name,
    t.test_name,
    coalesce(r.runs, 0)                                     as runs,
    coalesce(r.fails, 0)                                    as fails,
    r.fails / nullif(r.runs, 0)                             as fail_rate,
    coalesce(d.divergent_commits, 0)                        as divergent_commits,
    coalesce(d.commits_run_on, 0)                           as commits_run_on,
    coalesce(d.divergent_commits, 0) > 0                    as is_flaky,
    coalesce(f.flip_rate, 0)                                as flip_rate_30d,
    coalesce(f.flips_in_window, 0)                          as flips_30d,
    coalesce(f.pairs_in_window, 0)                          as pairs_30d,
    coalesce(g.regression_episodes, 0)                      as regression_episodes,
    coalesce(g.regression_episodes, 0) > 0                  as has_regressed,
    g.first_regression_commit_key,
    g.first_regression_at_utc
from {{ ref('dim_test') }} as t
left join runs as r using (test_key)
left join divergence as d using (test_key)
left join latest_flip_rate as f using (test_key)
left join regressions as g using (test_key)
