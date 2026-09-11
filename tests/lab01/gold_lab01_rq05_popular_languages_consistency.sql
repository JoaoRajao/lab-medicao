with rq05 as (
    select *
    from {{ ref('gold_lab01_rq05_popular_languages') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq05
    having sum(repositories_count) != 1000

    union all

    select 'repositories_pct_not_approximately_100' as failure_reason
    from rq05
    having sum(repositories_pct) not between 99.9 and 100.1

    union all

    select 'missing_language_group' as failure_reason
    from rq05
    where primary_language is null

    union all

    select 'invalid_repository_count' as failure_reason
    from rq05
    where repositories_count <= 0

    union all

    select 'popular_language_source_mismatch' as failure_reason
    from rq05
    where popular_language_source != 'GitHub Octoverse 2025'
        or popular_language_source_url != 'https://octoverse.github.com/'
)

select *
from failures
