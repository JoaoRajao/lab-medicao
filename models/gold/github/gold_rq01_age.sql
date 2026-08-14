{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        age_days
    from {{ ref('stg_github_repositories') }}
)

select
    count(*) as total_repositories,
    round(avg(age_days), 2) as avg_age_days,
    median(age_days) as median_age_days,
    min(age_days) as min_age_days,
    max(age_days) as max_age_days
from repositories
