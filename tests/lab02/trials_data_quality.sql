with trials as (
    select *
    from {{ ref('stg_lab02_trials') }}
),

failures as (
    select 'unexpected_treatment' as failure_reason
    from trials
    where treatment not in ('manual', 'ai_assisted')

    union all

    select 'invalid_timebox' as failure_reason
    from trials
    where timebox_seconds <= 0
        or timebox_seconds > 2100
        or time_to_green_seconds < 0
        or time_to_green_seconds > timebox_seconds

    union all

    select 'negative_test_count' as failure_reason
    from trials
    where tests_passed < 0
        or tests_failed < 0

    union all

    select 'success_rate_out_of_range' as failure_reason
    from trials
    where acceptance_success_rate < 0
        or acceptance_success_rate > 1

    union all

    select 'negative_static_metric' as failure_reason
    from trials
    where cyclomatic_complexity_avg < 0
        or cyclomatic_complexity_max < 0
        or maintainability_index < 0
        or loc < 0
        or lloc < 0
        or sloc < 0
        or duplication_pct < 0
)

select *
from failures
