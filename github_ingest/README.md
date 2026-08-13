# GitHub ingest para DuckDB, Parquet e dbt

Aplicacao simples em Python para coletar repositorios populares do GitHub e gerar uma base analitica para responder as RQs do laboratorio.

## Fonte de linguagens populares

Este projeto usa uma unica referencia para classificar `is_popular_language`:

- Fonte: GitHub Octoverse 2025
- URL: https://octoverse.github.com/
- Definicao usada: TypeScript como linguagem #1 e o grupo principal citado para novos repositorios: Python, JavaScript, TypeScript, Java, C++ e C#.

A lista fica em `config/popular_languages.json` para manter a referencia explicita e reutilizavel.

## Instalar

```bash
cd github_ingest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` e informe `GITHUB_TOKEN`. O token aumenta o limite da API e evita falhas por rate limit.

## Executar

Coletar os 1.000 repositorios mais populares por estrelas:

```bash
python ingest_github.py
```

Se a coleta parar ou o terminal fechar, rode o mesmo comando novamente. O script usa checkpoint e pula os repositorios ja coletados:

```bash
python ingest_github.py
```

Para uma coleta mais conservadora com a Search API:

```bash
python ingest_github.py --search-sleep 3
```

Com outro criterio de busca:

```bash
python ingest_github.py --query "stars:>10000 archived:false" --limit 200
```

Para refazer a coleta do zero, ignorando o checkpoint:

```bash
python ingest_github.py --no-resume
```

Observacao: a GitHub Search API retorna no maximo os primeiros 1.000 resultados por busca. Para essa coleta, configure `GITHUB_TOKEN`; sem token, o limite da API nao sustenta a mineracao completa.

## Saidas

- DuckDB: `data/github.duckdb`
- Parquet: `data/parquet/repositories.parquet`
- Checkpoint: `data/checkpoints/repositories.jsonl`
- Tabela DuckDB: `github_repositories`

## Metricas geradas

- RQ01: `age_days`, calculado a partir de `created_at`
- RQ02: `accepted_pull_requests`, total de PRs com merge
- RQ03: `releases_count`, total de releases
- RQ04: `days_since_last_update`, calculado a partir de `pushed_at`
- RQ05: `primary_language`, `is_popular_language`
- RQ06: `closed_issues_ratio`, `closed_issues_count`, `total_issues_count`
- RQ07: comparar `is_popular_language` contra PRs aceitas, releases e atualizacao

## dbt

Os modelos em `models/staging/github` leem a tabela `github_repositories` no mesmo DuckDB gerado pela ingestao. Depois de executar a ingestao:

```bash
cd ..
dbt run --select staging.github gold.github
```
