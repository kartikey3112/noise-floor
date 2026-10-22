-- Grain: one row per demo test. Compares what each demo test was designed to do (the answer
-- key) with what the metrics found, so the README can say how well detection worked.
--   flaky       -> should be flagged flaky (diverged on at least one commit)
--   slows_down  -> should regress, starting on its designed slowdown commit, and not be flaky
--   stable      -> should be neither flaky nor regressed

select
    t.test_name,
    t.designed_as,
    t.designed_cause,
    t.designed_fail_rate,
    h.fail_rate                                                 as observed_fail_rate,
    h.is_flaky,
    h.divergent_commits,
    h.has_regressed,
    t.designed_slowdown_commit_sha,
    c.commit_sha                                                as first_regression_commit_sha,
    case t.designed_as
        when 'flaky' then h.is_flaky
        when 'slows_down' then
            h.has_regressed and not h.is_flaky
            and c.commit_sha = t.designed_slowdown_commit_sha
        when 'stable' then not h.is_flaky and not h.has_regressed
    end                                                         as detected_as_designed
from {{ ref('dim_test') }} as t
join {{ ref('mart_test_health') }} as h using (test_key)
left join {{ ref('dim_commit') }} as c on c.commit_key = h.first_regression_commit_key
where t.is_demo
