{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        days_since_last_update
    from {{ ref('stg_lab01_repos_populares') }}
)

select
    count(*) as total_repositories,
    round(avg(days_since_last_update), 2) as avg_days_since_last_update,
    median(days_since_last_update) as median_days_since_last_update,
    min(days_since_last_update) as min_days_since_last_update,
    max(days_since_last_update) as max_days_since_last_update
from repositories
