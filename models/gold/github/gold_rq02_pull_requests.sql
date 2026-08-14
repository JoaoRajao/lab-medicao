{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        accepted_pull_requests
    from {{ ref('stg_github_repositories') }}
)

select
    count(*) as total_repositories,
    round(avg(accepted_pull_requests), 2) as avg_accepted_pull_requests,
    median(accepted_pull_requests) as median_accepted_pull_requests,
    min(accepted_pull_requests) as min_accepted_pull_requests,
    max(accepted_pull_requests) as max_accepted_pull_requests
from repositories
