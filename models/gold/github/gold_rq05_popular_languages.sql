{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        full_name,
        coalesce(primary_language, 'Unknown') as primary_language,
        is_popular_language,
        popular_language_source,
        popular_language_source_url,
        stars_count
    from {{ ref('stg_github_repositories') }}
),

totals as (
    select count(*) as total_repositories
    from repositories
)

select
    repositories.primary_language,
    repositories.is_popular_language,
    repositories.popular_language_source,
    repositories.popular_language_source_url,
    count(*) as repositories_count,
    round(count(*) * 100.0 / totals.total_repositories, 2) as repositories_pct,
    sum(repositories.stars_count) as stars_count,
    round(avg(repositories.stars_count), 2) as avg_stars_count
from repositories
cross join totals
group by
    repositories.primary_language,
    repositories.is_popular_language,
    repositories.popular_language_source,
    repositories.popular_language_source_url,
    totals.total_repositories
order by repositories_count desc, stars_count desc
