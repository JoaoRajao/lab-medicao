{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        releases_count
    from {{ ref('stg_github_repositories') }}
)

select
    count(*) as total_repositories,
    round(avg(releases_count), 2) as avg_releases_count,
    median(releases_count) as median_releases_count,
    min(releases_count) as min_releases_count,
    max(releases_count) as max_releases_count
from repositories
