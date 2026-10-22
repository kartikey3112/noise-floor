-- Grain: one row per commit SHA that Jenkins built.
-- commit_seq numbers the commits in the order they were first built (1 = earliest).
-- subject comes from the demo seed; it's empty for any commit the seed doesn't know.

with builds as (
    select b.commit_sha, t.started_at_utc
    from {{ ref('stg_jenkins__builds') }} as b
    join {{ ref('int_build_times') }} as t using (job_name, build_number)
),

per_commit as (
    select
        commit_sha,
        min(started_at_utc) as first_built_at_utc,
        max(started_at_utc) as last_built_at_utc,
        count(*)            as builds_count
    from builds
    group by commit_sha
)

select
    {{ surrogate_key(['c.commit_sha']) }}               as commit_key,
    c.commit_sha,
    left(c.commit_sha, 7)                               as short_sha,
    row_number() over (order by c.first_built_at_utc)   as commit_seq,
    s.subject,
    c.first_built_at_utc,
    c.last_built_at_utc,
    c.builds_count
from per_commit as c
left join {{ ref('demo_commits') }} as s using (commit_sha)
