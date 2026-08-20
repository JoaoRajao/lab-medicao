with rq07 as (
    select *
    from {{ ref('gold_rq07_popular_language_comparison') }}
),

failures as (
    select 'expected_two_language_groups' as failure_reason
    from rq07
    having count(*) != 2

    union all

    select 'expected_1000_repositories' as failure_reason
    from rq07
    having sum(repositories_count) != 1000

    union all

    select 'unexpected_language_group' as failure_reason
    from rq07
    where language_group not in ('linguagem_popular', 'outras_linguagens')

    union all

    select 'invalid_repository_count' as failure_reason
    from rq07
    where repositories_count <= 0

    union all

    select 'negative_contribution_or_release_metric' as failure_reason
    from rq07
    where avg_accepted_pull_requests < 0
        or median_accepted_pull_requests < 0
        or min_accepted_pull_requests < 0
        or max_accepted_pull_requests < 0
        or avg_releases_count < 0
        or median_releases_count < 0
        or min_releases_count < 0
        or max_releases_count < 0
        or avg_days_since_last_update < 0
        or median_days_since_last_update < 0
        or min_days_since_last_update < 0
        or max_days_since_last_update < 0
)

select *
from failures
