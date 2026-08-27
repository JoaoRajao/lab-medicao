with rq03 as (
    select *
    from {{ ref('gold_lab01_rq03_releases') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq03
    where total_repositories != 1000

    union all

    select 'negative_releases_metric' as failure_reason
    from rq03
    where avg_releases_count < 0
        or median_releases_count < 0
        or min_releases_count < 0
        or max_releases_count < 0

    union all

    select 'inconsistent_bounds' as failure_reason
    from rq03
    where min_releases_count > max_releases_count
        or avg_releases_count > max_releases_count
        or min_releases_count > avg_releases_count
)

select *
from failures
