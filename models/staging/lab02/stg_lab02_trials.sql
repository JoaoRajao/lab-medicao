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
    cast(started_at as timestamptz) as started_at,
    cast(finished_at as timestamptz) as finished_at
from read_parquet('labs/lab02_ia_vs_manual/data/parquet/trials.parquet')
