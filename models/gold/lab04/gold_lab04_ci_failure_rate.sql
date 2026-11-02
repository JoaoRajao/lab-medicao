{{ config(materialized='table') }}

select
    repository,
    workflow_id,
    count(*) as runs_count,
    sum(failed) as failures_count,
    sum(failed) * 1.0 / count(*) as failure_rate,
    min(created_at) as first_run_at,
    max(created_at) as last_run_at
from {{ ref('stg_lab04_ci_runs') }}
group by repository, workflow_id
