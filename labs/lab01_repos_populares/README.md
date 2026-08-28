# Lab01 - Mineracao de repositorios populares do GitHub

Coleta os 1.000 repositorios com mais estrelas do GitHub via GraphQL e responde as RQ01-RQ07 do
laboratorio (idade, contribuicao externa, releases, frequencia de atualizacao, linguagens
populares, percentual de issues fechadas, e o cruzamento de linguagem popular com atividade).

Este e o unico lab que sabe o que e um "repositorio do GitHub" -- toda a mecanica de HTTP,
paginacao, checkpoint e escrita no warehouse vem de `shared/` (ver README da raiz).

A query GraphQL esta em `ingest.py`, escrita e consumida com `urllib` da biblioteca padrao (via
`shared/github_client.py`). Sem PyGithub, GitHub SDK, GraphQL client externo ou biblioteca de
terceiros para consultar a API.

## Fonte de linguagens populares

Referencia unica para classificar `is_popular_language`, usada em todo o laboratorio:

- Fonte: GitHub Octoverse 2025
- URL: https://octoverse.github.com/
- Definicao: TypeScript, Python, JavaScript, Java, C++ e C#.
- Arquivo: `config/popular_languages.json`

## Rodar (a partir da raiz do repositorio, com o ambiente da raiz ativado)

```bash
cp labs/lab01_repos_populares/.env.example .env   # se ainda nao existir; edite com seu GITHUB_TOKEN
python -m labs.lab01_repos_populares.ingest
```

Coleta os 1.000 repositorios mais populares por estrelas. Se parar por rate limit ou interrupcao,
rode o mesmo comando de novo -- usa checkpoint e pula repositorios ja coletados:

```bash
python -m labs.lab01_repos_populares.ingest
```

Com outro criterio de busca:

```bash
python -m labs.lab01_repos_populares.ingest --query "stars:>10000 archived:false" --limit 200
```

Para refazer a coleta do zero, ignorando o checkpoint:

```bash
python -m labs.lab01_repos_populares.ingest --no-resume
```

Para reexportar Parquet/CSV a partir do warehouse existente, sem bater na API de novo:

```bash
python -m labs.lab01_repos_populares.ingest --export-only
```

Observacao: a busca do GitHub retorna no maximo os primeiros 1.000 resultados. Para essa coleta,
configure `GITHUB_TOKEN`.

## Saidas

- Tabela no warehouse compartilhado: `lab01_repos_populares` (`data/warehouse.duckdb`, na raiz do repo)
- Parquet: `data/parquet/repositories.parquet`
- CSV: `data/csv/repositories.csv`
- Checkpoint: `data/checkpoints/repositories.jsonl`

## Metricas geradas

- RQ01: `age_days`, calculado a partir de `created_at`
- RQ02: `accepted_pull_requests`, total de PRs com merge
- RQ03: `releases_count`, total de releases
- RQ04: `days_since_last_update`, calculado a partir de `pushed_at`
- RQ05: `primary_language`, `is_popular_language`
- RQ06: `closed_issues_ratio`, `closed_issues_count`, `total_issues_count`
- RQ07: comparar `is_popular_language` contra PRs aceitas, releases e atualizacao

## dbt

Os modelos em `models/staging/lab01` leem a tabela `lab01_repos_populares` do warehouse
compartilhado. Depois de rodar a ingestao (a partir da raiz do repo):

```bash
dbt run --select staging.lab01 gold.lab01
dbt test --select staging.lab01 gold.lab01
```

Tabelas finais no warehouse:

- `gold_lab01_rq01_age` ... `gold_lab01_rq07_popular_language_comparison`

## Analise e visualizacao

```bash
python -m labs.lab01_repos_populares.visualize
```

Gera os graficos de distribuicao por faixa (RQ01, RQ02, RQ03, RQ04, RQ06, top linguagens de RQ05 e
a comparacao de RQ07) em `docs/lab01/assets/`, usando o motor de grafico generico de
`shared/viz/charts.py`. As faixas usadas em cada grafico sao identicas as publicadas nos documentos
de validacao (`docs/lab01/rq01_rq02_validacao.md`, `docs/lab01/rq03_rq04_validacao.md`,
`docs/lab01/rq05_rq07_validacao.md`).

Para gerar so alguns graficos:

```bash
python -m labs.lab01_repos_populares.visualize --rq rq01_age rq02_pull_requests
```

## DuckDB UI

Feche o dbt antes de abrir a UI, porque DuckDB usa lock no arquivo (a partir da raiz do repo):

```bash
duckdb -ui data/warehouse.duckdb
```

```sql
select * from gold_lab01_rq01_age;
select * from gold_lab01_rq05_popular_languages;
```
