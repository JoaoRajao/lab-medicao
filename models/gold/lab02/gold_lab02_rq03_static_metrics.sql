{{ config(materialized='table') }}

select
    treatment,
    count(*) as trials_count,
    round(avg(cyclomatic_complexity_avg), 4) as avg_cyclomatic_complexity,
    median(cyclomatic_complexity_avg) as median_cyclomatic_complexity,
    max(cyclomatic_complexity_max) as max_cyclomatic_complexity,
    round(avg(maintainability_index), 4) as avg_maintainability_index,
    median(maintainability_index) as median_maintainability_index,
    round(avg(loc), 2) as avg_loc,
    median(loc) as median_loc,
    round(avg(duplication_pct), 4) as avg_duplication_pct,
    median(duplication_pct) as median_duplication_pct
from {{ ref('stg_lab02_trials') }}
group by treatment
order by treatment
