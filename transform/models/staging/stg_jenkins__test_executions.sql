-- Grain: one row per test execution (job_name, build_number, case_index).
-- Maps Jenkins' statuses to the three outcomes every metric uses (decision D-016):
--   PASSED, FIXED     -> pass   (FIXED = passed after failing in the previous build)
--   FAILED, REGRESSED -> fail   (REGRESSED = failed after passing; JUnit errors arrive as FAILED)
--   SKIPPED           -> skip   (stored, but ignored by every metric)

select
    job_name,
    build_number,
    case_index,
    suite_name,
    class_name,
    test_name,
    status                          as jenkins_status,
    case
        when status in ('PASSED', 'FIXED') then 'pass'
        when status in ('FAILED', 'REGRESSED') then 'fail'
        when status = 'SKIPPED' then 'skip'
    end                             as outcome,
    duration_s,
    nullif(trim(split_part(error_details, chr(10), 1)), '') as error_message
from {{ source('raw', 'jenkins_test_cases') }}
