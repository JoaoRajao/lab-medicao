{{ config(materialized='table') }}

select
    treatment,
    count(*) as trials_count,
    round(avg(time_to_green_seconds), 2) as avg_time_to_green_seconds,
    median(time_to_green_seconds) as median_time_to_green_seconds,
    quantile_cont(time_to_green_seconds, 0.25) as q1_time_to_green_seconds,
    quantile_cont(time_to_green_seconds, 0.75) as q3_time_to_green_seconds,
    min(time_to_green_seconds) as min_time_to_green_seconds,
    max(time_to_green_seconds) as max_time_to_green_seconds,
    sum(case when censored then 1 else 0 end) as censored_trials
from {{ ref('stg_lab02_trials') }}
group by treatment
order by treatment
