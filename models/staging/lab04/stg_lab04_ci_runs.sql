{{ config(materialized='view') }}

select
    repository,
    workflow_id,
    run_id,
    run_attempt,
    head_sha,
    event,
    head_branch,
    created_at,
    conclusion,
    case when conclusion = 'failure' then 1 else 0 end as failed,
    html_url
from lab04_ci_runs
