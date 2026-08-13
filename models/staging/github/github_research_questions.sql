{{ config(materialized='view') }}

select
    full_name,
    stars_count,
    -- RQ01: sistemas populares sao maduros/antigos?
    age_days,
    -- RQ02: sistemas populares recebem muita contribuicao externa?
    accepted_pull_requests,
    -- RQ03: sistemas populares lancam releases com frequencia?
    releases_count,
    -- RQ04: sistemas populares sao atualizados com frequencia?
    days_since_last_update,
    -- RQ05: sistemas populares usam linguagens populares?
    primary_language,
    is_popular_language,
    popular_language_source,
    popular_language_source_url,
    -- RQ06: sistemas populares possuem alto percentual de issues fechadas?
    closed_issues_ratio,
    closed_issues_count,
    total_issues_count,
    collected_at
from {{ ref('stg_github_repositories') }}
