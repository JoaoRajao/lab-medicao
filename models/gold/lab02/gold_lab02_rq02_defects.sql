{{ config(materialized='table') }}

select
    treatment,
    count(*) as trials_count,
    sum(tests_passed) as tests_passed,
    sum(tests_failed) as tests_failed,
    round(avg(tests_failed), 4) as avg_tests_failed,
    median(tests_failed) as median_tests_failed,
    quantile_cont(tests_failed, 0.25) as q1_tests_failed,
    quantile_cont(tests_failed, 0.75) as q3_tests_failed,
    quantile_cont(tests_failed, 0.75) - quantile_cont(tests_failed, 0.25) as iqr_tests_failed,
    round(avg(acceptance_success_rate), 4) as avg_acceptance_success_rate,
    median(acceptance_success_rate) as median_acceptance_success_rate,
    quantile_cont(acceptance_success_rate, 0.25) as q1_acceptance_success_rate,
    quantile_cont(acceptance_success_rate, 0.75) as q3_acceptance_success_rate,
    quantile_cont(acceptance_success_rate, 0.75)
        - quantile_cont(acceptance_success_rate, 0.25) as iqr_acceptance_success_rate,
    sum(case when tests_failed = 0 then 1 else 0 end) as green_trials,
    round(sum(case when tests_failed = 0 then 1 else 0 end) * 1.0 / count(*), 4) as green_trial_rate
from {{ ref('stg_lab02_trials') }}
group by treatment
order by treatment
