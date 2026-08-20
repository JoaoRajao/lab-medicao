with rq06 as (
    select *
    from {{ ref('gold_rq06_closed_issues') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from rq06
    having sum(repositories_count) != 1000

    union all

    select 'unexpected_closed_issues_band' as failure_reason
    from rq06
    where closed_issues_band not in (
        'alto_80_100',
        'medio_50_79',
        'baixo_0_49',
        'sem_issues'
    )

    union all

    select 'invalid_repository_count' as failure_reason
    from rq06
    where repositories_count <= 0

    union all

    select 'closed_issues_ratio_out_of_range' as failure_reason
    from rq06
    where (
        avg_closed_issues_ratio is not null
        and (avg_closed_issues_ratio < 0 or avg_closed_issues_ratio > 1)
    )
        or (
            median_closed_issues_ratio is not null
            and (median_closed_issues_ratio < 0 or median_closed_issues_ratio > 1)
        )
        or (
            min_closed_issues_ratio is not null
            and (min_closed_issues_ratio < 0 or min_closed_issues_ratio > 1)
        )
        or (
            max_closed_issues_ratio is not null
            and (max_closed_issues_ratio < 0 or max_closed_issues_ratio > 1)
        )
        or (
            weighted_closed_issues_ratio is not null
            and (weighted_closed_issues_ratio < 0 or weighted_closed_issues_ratio > 1)
        )

    union all

    select 'closed_issues_greater_than_total' as failure_reason
    from rq06
    where closed_issues_count > total_issues_count
)

select *
from failures
