{{ config(severity='warn') }}

-- Warns when a build has far fewer test results than the build before it, per suite.
-- Example: unit had 133 results in build 20 and 0 in build 21, so a JUnit file went missing,
-- or a stage stopped early. Tests can be removed on purpose, so this warns instead of failing.

with per_suite as (
    select job_name, build_number, suite_name, count(*) as results
    from {{ source('raw', 'jenkins_test_cases') }}
    group by job_name, build_number, suite_name
),

all_suites as (
    -- Every build x every suite ever seen, so a suite that vanished shows up as 0 results.
    select b.job_name, b.build_number, s.suite_name, coalesce(p.results, 0) as results
    from {{ source('raw', 'jenkins_builds') }} as b
    cross join (select distinct suite_name from per_suite) as s
    left join per_suite as p using (job_name, build_number, suite_name)
    where b.result in ('SUCCESS', 'UNSTABLE')
),

compared as (
    select
        *,
        lag(results) over (
            partition by job_name, suite_name order by build_number
        ) as previous_results
    from all_suites
)

select job_name, build_number, suite_name, previous_results, results
from compared
where previous_results > 0
  and results < 0.9 * previous_results  -- lost more than 10% of the suite's results
