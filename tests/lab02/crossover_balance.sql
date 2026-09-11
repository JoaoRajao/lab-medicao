with participant_treatments as (
    select
        participant,
        treatment,
        count(*) as trials_count
    from {{ ref('stg_lab02_trials') }}
    group by participant, treatment
),

participant_totals as (
    select
        participant,
        count(distinct kata) as katas_count,
        count(*) as trials_count
    from {{ ref('stg_lab02_trials') }}
    group by participant
),

failures as (
    select 'participant_without_6_katas' as failure_reason
    from participant_totals
    where katas_count != 6
        or trials_count != 6

    union all

    select 'participant_without_3_trials_per_treatment' as failure_reason
    from participant_treatments
    where trials_count != 3

    union all

    select 'participant_missing_treatment' as failure_reason
    from participant_totals totals
    where (
        select count(*)
        from participant_treatments treatments
        where treatments.participant = totals.participant
    ) != 2
)

select *
from failures
