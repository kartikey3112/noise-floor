-- Grain: one row per passed test execution, checked against the test's own baseline.
--
-- Baseline: the median duration of the test's previous N passed runs (var
-- regression_baseline_runs). Only passed runs count: a test that fails early looks fast and
-- would drag the baseline down (ADR-010).
-- Regression: more than ratio x the baseline AND at least min_increase_s longer, with at least
-- min_baseline_runs earlier passed runs. Example: baseline 0.20 s, this run 1.24 s
-- -> 6.2x and +1.04 s, so it's a regression. A 0.01 s test taking 0.40 s is 40x but only
-- +0.39 s, so it isn't: the floor keeps tiny tests from raising alarms over noise.

with passed as (
    select
        execution_key,
        test_key,
        build_key,
        commit_key,
        executed_at_utc,
        test_run_seq,
        duration_s
    from {{ ref('fct_test_executions') }}
    where outcome = 'pass'
),

with_baseline as (
    select
        *,
        median(duration_s) over earlier_runs   as baseline_median_s,
        count(*) over earlier_runs             as baseline_runs
    from passed
    window earlier_runs as (
        partition by test_key
        order by test_run_seq
        rows between {{ var('regression_baseline_runs') }} preceding and 1 preceding
    )
)

select
    *,
    duration_s / nullif(baseline_median_s, 0)  as duration_ratio,
    duration_s - baseline_median_s             as increase_s,
    coalesce(
        baseline_runs >= {{ var('regression_min_baseline_runs') }}
        and duration_s > {{ var('regression_ratio') }} * baseline_median_s
        and duration_s - baseline_median_s >= {{ var('regression_min_increase_s') }},
        false
    )                                          as is_regression
from with_baseline
