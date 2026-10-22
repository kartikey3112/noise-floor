-- A build that ran its tests (SUCCESS or UNSTABLE) must have test results in the raw layer.
-- If one has none, ingestion lost its test report, or Jenkins never published it.
-- A FAILURE can legitimately have none: the pipeline may have broken before tests ran.

select b.job_name, b.build_number, b.result
from {{ source('raw', 'jenkins_builds') }} as b
where b.result in ('SUCCESS', 'UNSTABLE')
  and not exists (
      select 1
      from {{ source('raw', 'jenkins_test_cases') }} as c
      where c.job_name = b.job_name and c.build_number = b.build_number
  )
