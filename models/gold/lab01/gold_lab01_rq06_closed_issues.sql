{{ config(materialized='table') }}

with repositories as (
    select
        repo_id,
        full_name,
        stars_count,
        closed_issues_count,
        total_issues_count,
        closed_issues_ratio,
        case
            when total_issues_count = 0 then 'sem_issues'
            when closed_issues_ratio >= 0.80 then 'alto_80_100'
            when closed_issues_ratio >= 0.50 then 'medio_50_79'
            else 'baixo_0_49'
        end as closed_issues_band
    from {{ ref('stg_lab01_repos_populares') }}
)

select
    closed_issues_band,
    count(*) as repositories_count,
    round(avg(closed_issues_ratio), 4) as avg_closed_issues_ratio,
    round(median(closed_issues_ratio), 4) as median_closed_issues_ratio,
    min(closed_issues_ratio) as min_closed_issues_ratio,
    max(closed_issues_ratio) as max_closed_issues_ratio,
    sum(closed_issues_count) as closed_issues_count,
    sum(total_issues_count) as total_issues_count,
    round(
        sum(closed_issues_count) * 1.0 / nullif(sum(total_issues_count), 0),
        4
    ) as weighted_closed_issues_ratio
from repositories
group by closed_issues_band
order by
    case closed_issues_band
        when 'alto_80_100' then 1
        when 'medio_50_79' then 2
        when 'baixo_0_49' then 3
        else 4
    end
