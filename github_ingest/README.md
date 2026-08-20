# GitHub ingest para DuckDB, Parquet e dbt

Aplicacao simples em Python para coletar repositorios populares do GitHub via GraphQL e gerar uma base analitica para responder as RQs do laboratorio.

A query GraphQL esta escrita em `ingest_github.py` e e consumida diretamente pelo script com `urllib`, da biblioteca padrao do Python. O projeto nao usa PyGithub, GitHub SDK, GraphQL client externo ou biblioteca de terceiros para consultar a API do GitHub.

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

Com outro criterio de busca:

```bash
python ingest_github.py --query "stars:>10000 archived:false" --limit 200
```

Para refazer a coleta do zero, ignorando o checkpoint:

```bash
python ingest_github.py --no-resume
```

Observacao: a busca do GitHub retorna no maximo os primeiros 1.000 resultados. Para essa coleta, configure `GITHUB_TOKEN`.

## Saidas

- DuckDB: `data/github.duckdb`
- Parquet: `data/parquet/repositories.parquet`
- CSV: `data/csv/repositories.csv`
- Checkpoint: `data/checkpoints/repositories.jsonl`
- Tabela DuckDB: `github_repositories`

Para reexportar so o CSV a partir dos dados ja coletados no DuckDB, sem bater na API de novo:

```bash
python ingest_github.py --export-only
```

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

## Snapshot de fechamento de sprint

O GitHub Projects (v2) nao guarda historico de mudancas de coluna consultavel via API. Para isso, ao final de cada sprint rodamos `export_project_snapshot.py`, que reaproveita o `GitHubGraphQLClient` de `ingest_github.py` para consultar os itens do Project e o status atual de cada um, gravando um CSV.

O token em `.env` precisa do escopo `read:project` (PAT classico) ou da permissao "Projects: Read" (fine-grained), alem do acesso normal ao repositorio.

```bash
python export_project_snapshot.py --sprint Lab01S01
```

Gera `data/project_snapshots/snapshot_Lab01S01_<data>.csv` com uma linha por item do Project: `issue_number`, `title`, `repository`, `assignees`, `status` (coluna do board) e `exported_at`.

Esses CSVs sao versionados (nao entram no `.gitignore`) porque formam a serie de snapshots sprint a sprint que serve de base para os Labs 04 e 05.
