-- Grain: one row per regression episode: a run of consecutive flagged passed executions of
-- one test.
--
-- After a real slowdown, every later run is flagged until the slow runs fill most of the
-- baseline and the median catches up ("the new normal"). An episode groups those runs, and
-- its onset says when and on which commit the slowdown started.

with checks as (
    select
        *,
        lag(is_regression, 1, false) over by_run as previous_was_regression
    from {{ ref('mart_runtime_checks') }}
    window by_run as (partition by test_key order by test_run_seq)
),

numbered as (
    -- Each onset starts a new episode number; later runs in the episode keep it.
    select
        *,
        sum(case when is_regression and not previous_was_regression then 1 else 0 end)
            over (partition by test_key order by test_run_seq) as episode_number
    from checks
),

episodes as (
    select
        test_key,
        episode_number,
        count(*)                                        as flagged_runs,
        arg_min(execution_key, test_run_seq)            as onset_execution_key,
        arg_min(build_key, test_run_seq)                as onset_build_key,
        arg_min(commit_key, test_run_seq)               as onset_commit_key,
        min(executed_at_utc)                            as onset_at_utc,
        max(executed_at_utc)                            as last_flagged_at_utc,
        arg_min(baseline_median_s, test_run_seq)        as baseline_median_s,
        arg_min(duration_s, test_run_seq)               as onset_duration_s,
        arg_min(duration_ratio, test_run_seq)           as onset_duration_ratio
    from numbered
    where is_regression
    group by test_key, episode_number
)

select
    {{ surrogate_key(['test_key', 'onset_execution_key']) }} as regression_key,
    *
from episodes
