with repositories as (
    select *
    from {{ ref('stg_github_repositories') }}
),

failures as (
    select 'expected_1000_repositories' as failure_reason
    from repositories
    having count(*) != 1000

    union all

    select 'popular_language_source_mismatch' as failure_reason
    from repositories
    where popular_language_source != 'GitHub Octoverse 2025'
        or popular_language_source_url != 'https://octoverse.github.com/'

    union all

    select 'negative_activity_metric' as failure_reason
    from repositories
    where stars_count < 0
        or forks_count < 0
        or watchers_count < 0
        or open_issues_count < 0
        or closed_issues_count < 0
        or total_issues_count < 0
        or accepted_pull_requests < 0
        or releases_count < 0
        or age_days < 0
        or days_since_last_update < 0

    union all

    select 'issues_total_mismatch' as failure_reason
    from repositories
    where total_issues_count != open_issues_count + closed_issues_count

    union all

    select 'closed_issues_ratio_out_of_range' as failure_reason
    from repositories
    where closed_issues_ratio is not null
        and (closed_issues_ratio < 0 or closed_issues_ratio > 1)

    union all

    select 'closed_issues_ratio_null_mismatch' as failure_reason
    from repositories
    where (total_issues_count = 0 and closed_issues_ratio is not null)
        or (total_issues_count > 0 and closed_issues_ratio is null)
)

select *
from failures
