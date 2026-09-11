{{ config(materialized='view') }}

select
    trial_id,
    participant,
    kata,
    treatment,
    assistant,
    timebox_seconds,
    time_to_green_seconds,
    censored,
    tests_passed,
    tests_failed,
    acceptance_success_rate,
    cyclomatic_complexity_avg,
    cyclomatic_complexity_max,
    maintainability_index,
    loc,
    lloc,
    sloc,
    duplication_pct,
    solution_path,
    started_at,
    finished_at
from lab02_trials
