with repositories as (
    select *
    from {{ ref('stg_lab01_repos_populares') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from repositories
    having count(*) != 1000

    union all

    select 'negative_age_days' as failure_reason
    from repositories
    where age_days < 0

    union all

    select 'negative_accepted_pull_requests' as failure_reason
    from repositories
    where accepted_pull_requests < 0

    union all

    select 'negative_releases_count' as failure_reason
    from repositories
    where releases_count < 0

    union all

    select 'negative_days_since_last_update' as failure_reason
    from repositories
    where days_since_last_update < 0

    union all

    select 'created_in_future' as failure_reason
    from repositories
    where created_at > collected_at
)

select *
from failures
