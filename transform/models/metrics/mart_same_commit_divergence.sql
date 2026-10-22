-- Grain: one row per (test, commit) the test ran on.
--
-- Same-commit divergence: a test is flaky on a commit if it both passed and failed there.
-- Example: test X passed on commit abc123 in build 4 and failed on abc123 in build 5, so it
-- diverged on abc123. Skipped runs say nothing about pass or fail and are ignored.

select
    test_key,
    commit_key,
    count(*) filter (where outcome = 'pass')            as passes,
    count(*) filter (where outcome = 'fail')            as fails,
    count(*) filter (where outcome = 'pass') > 0
        and count(*) filter (where outcome = 'fail') > 0 as is_divergent,
    min(executed_at_utc)                                as first_executed_at_utc,
    max(executed_at_utc)                                as last_executed_at_utc
from {{ ref('fct_test_executions') }}
where outcome in ('pass', 'fail')
group by test_key, commit_key
