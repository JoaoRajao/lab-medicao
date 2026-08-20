with rq04 as (
    select *
    from {{ ref('gold_rq04_updates') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq04
    where total_repositories != 1000

    union all

    select 'negative_updates_metric' as failure_reason
    from rq04
    where avg_days_since_last_update < 0
        or median_days_since_last_update < 0
        or min_days_since_last_update < 0
        or max_days_since_last_update < 0

    union all

    select 'inconsistent_bounds' as failure_reason
    from rq04
    where min_days_since_last_update > max_days_since_last_update
        or avg_days_since_last_update > max_days_since_last_update
        or min_days_since_last_update > avg_days_since_last_update
)

select *
from failures
