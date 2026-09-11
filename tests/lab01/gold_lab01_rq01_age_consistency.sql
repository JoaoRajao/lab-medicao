with rq01 as (
    select *
    from {{ ref('gold_lab01_rq01_age') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq01
    where total_repositories != 1000

    union all

    select 'negative_age_metric' as failure_reason
    from rq01
    where avg_age_days < 0
        or median_age_days < 0
        or min_age_days < 0
        or max_age_days < 0

    union all

    select 'inconsistent_bounds' as failure_reason
    from rq01
    where min_age_days > max_age_days
        or avg_age_days > max_age_days
        or min_age_days > avg_age_days
)

select *
from failures
