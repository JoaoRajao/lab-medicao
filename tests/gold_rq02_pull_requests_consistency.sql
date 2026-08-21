with rq02 as (
    select *
    from {{ ref('gold_rq02_pull_requests') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq02
    where total_repositories != 1000

    union all

    select 'negative_pull_requests_metric' as failure_reason
    from rq02
    where avg_accepted_pull_requests < 0
        or median_accepted_pull_requests < 0
        or min_accepted_pull_requests < 0
        or max_accepted_pull_requests < 0

    union all

    select 'inconsistent_bounds' as failure_reason
    from rq02
    where min_accepted_pull_requests > max_accepted_pull_requests
        or avg_accepted_pull_requests > max_accepted_pull_requests
        or min_accepted_pull_requests > avg_accepted_pull_requests
)

select *
from failures
