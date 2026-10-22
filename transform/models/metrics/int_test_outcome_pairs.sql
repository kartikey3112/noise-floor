-- Grain: one row per pair of consecutive executions of the same test, skips left out.
--
-- Executions are put in time order per test; each one is paired with the one before it.
-- Example: outcomes P, P, F, P give three pairs (P,P) (P,F) (F,P), and two of them flip.
-- A skip in between is dropped first, so P, skip, F is one pair (P,F) and one flip.

with outcomes as (
    select test_key, execution_key, executed_at_utc, test_run_seq, outcome
    from {{ ref('fct_test_executions') }}
    where outcome in ('pass', 'fail')
),

paired as (
    select
        test_key,
        lag(execution_key) over by_time     as previous_execution_key,
        lag(outcome) over by_time           as previous_outcome,
        lag(executed_at_utc) over by_time   as previous_executed_at_utc,
        execution_key,
        outcome,
        executed_at_utc
    from outcomes
    window by_time as (partition by test_key order by test_run_seq)
)

select
    *,
    outcome <> previous_outcome as is_flip
from paired
where previous_outcome is not null
