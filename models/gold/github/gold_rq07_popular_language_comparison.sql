{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        case
            when is_popular_language then 'linguagem_popular'
            else 'outras_linguagens'
        end as language_group,
        accepted_pull_requests,
        releases_count,
        days_since_last_update
    from {{ ref('stg_github_repositories') }}
)

select
    language_group,
    count(*) as repositories_count,
    round(avg(accepted_pull_requests), 2) as avg_accepted_pull_requests,
    median(accepted_pull_requests) as median_accepted_pull_requests,
    min(accepted_pull_requests) as min_accepted_pull_requests,
    max(accepted_pull_requests) as max_accepted_pull_requests,
    round(avg(releases_count), 2) as avg_releases_count,
    median(releases_count) as median_releases_count,
    min(releases_count) as min_releases_count,
    max(releases_count) as max_releases_count,
    round(avg(days_since_last_update), 2) as avg_days_since_last_update,
    median(days_since_last_update) as median_days_since_last_update,
    min(days_since_last_update) as min_days_since_last_update,
    max(days_since_last_update) as max_days_since_last_update
from repositories
group by language_group
order by language_group
