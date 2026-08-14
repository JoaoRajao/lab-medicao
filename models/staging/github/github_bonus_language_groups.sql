{{ config(materialized='view') }}

select
    is_popular_language,
    count(*) as repositories_count,
    avg(accepted_pull_requests) as avg_accepted_pull_requests,
    median(accepted_pull_requests) as median_accepted_pull_requests,
    avg(releases_count) as avg_releases_count,
    median(releases_count) as median_releases_count,
    avg(days_since_last_update) as avg_days_since_last_update,
    median(days_since_last_update) as median_days_since_last_update
from {{ ref('stg_github_repositories') }}
group by 1
