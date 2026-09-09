with rq01 as (
    select treatment, trials_count from {{ ref('gold_lab02_rq01_time') }}
),

rq02 as (
    select treatment, trials_count from {{ ref('gold_lab02_rq02_defects') }}
),

rq03 as (
    select treatment, trials_count from {{ ref('gold_lab02_rq03_static_metrics') }}
),

failures as (
    select 'rq01_expected_two_treatments' as failure_reason
    from rq01
    having count(*) != 2

    union all

    select 'rq02_expected_two_treatments' as failure_reason
    from rq02
    having count(*) != 2

    union all

    select 'rq03_expected_two_treatments' as failure_reason
    from rq03
    having count(*) != 2

    union all

    select 'rq01_expected_18_trials' as failure_reason
    from rq01
    having sum(trials_count) != 18

    union all

    select 'rq02_expected_18_trials' as failure_reason
    from rq02
    having sum(trials_count) != 18

    union all

    select 'rq03_expected_18_trials' as failure_reason
    from rq03
    having sum(trials_count) != 18
)

select *
from failures
