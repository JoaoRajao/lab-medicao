{{ config(materialized='table') }}

select
    treatment,
    count(*) as trials_count,
    round(avg(cyclomatic_complexity_avg), 4) as avg_cyclomatic_complexity,
    median(cyclomatic_complexity_avg) as median_cyclomatic_complexity,
    quantile_cont(cyclomatic_complexity_avg, 0.25) as q1_cyclomatic_complexity,
    quantile_cont(cyclomatic_complexity_avg, 0.75) as q3_cyclomatic_complexity,
    quantile_cont(cyclomatic_complexity_avg, 0.75)
        - quantile_cont(cyclomatic_complexity_avg, 0.25) as iqr_cyclomatic_complexity,
    max(cyclomatic_complexity_max) as max_cyclomatic_complexity,
    round(avg(maintainability_index), 4) as avg_maintainability_index,
    median(maintainability_index) as median_maintainability_index,
    quantile_cont(maintainability_index, 0.25) as q1_maintainability_index,
    quantile_cont(maintainability_index, 0.75) as q3_maintainability_index,
    quantile_cont(maintainability_index, 0.75)
        - quantile_cont(maintainability_index, 0.25) as iqr_maintainability_index,
    round(avg(loc), 2) as avg_loc,
    median(loc) as median_loc,
    quantile_cont(loc, 0.25) as q1_loc,
    quantile_cont(loc, 0.75) as q3_loc,
    quantile_cont(loc, 0.75) - quantile_cont(loc, 0.25) as iqr_loc,
    round(avg(duplication_pct), 4) as avg_duplication_pct,
    median(duplication_pct) as median_duplication_pct,
    quantile_cont(duplication_pct, 0.25) as q1_duplication_pct,
    quantile_cont(duplication_pct, 0.75) as q3_duplication_pct,
    quantile_cont(duplication_pct, 0.75)
        - quantile_cont(duplication_pct, 0.25) as iqr_duplication_pct
from {{ ref('stg_lab02_trials') }}
group by treatment
order by treatment
