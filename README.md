# Dataplataform TI6 - Mineracao GitHub com DuckDB e dbt

Projeto para coletar dados dos 1.000 repositorios mais populares do GitHub, gravar a base em DuckDB/Parquet e gerar tabelas analiticas com dbt para responder as questoes de pesquisa do laboratorio.

A coleta usa uma query GraphQL escrita no proprio script do projeto e consumida via biblioteca padrao do Python (`urllib`). Nao ha uso de PyGithub, GitHub SDK, GraphQL client externo ou biblioteca de terceiros para consultar a API do GitHub.

## Estrutura

```text
github_ingest/
  ingest_github.py              # Coleta dados da API GraphQL do GitHub
  requirements.txt              # Dependencias Python da ingestao
  .env.example                  # Exemplo de variaveis de ambiente
  config/popular_languages.json # Fonte usada para linguagens populares
models/
  staging/github/               # Camada staging
  gold/github/                  # Tabelas finais para RQs
profiles.example.yml            # Exemplo de profile dbt com DuckDB
```

## Dados que nao sobem para o Git

Os seguintes arquivos sao gerados localmente e estao no `.gitignore`:

- `github_ingest/.env`
- `github_ingest/.venv/`
- `github_ingest/data/github.duckdb`
- `github_ingest/data/checkpoints/*.jsonl`
- `dev.duckdb`
- `target/`
- `logs/`

O arquivo `github_ingest/data/parquet/repositories.parquet` sobe para o repositorio para facilitar a avaliacao sem reprocessar a API. Nao commite tokens, bancos locais, venv, logs ou checkpoints.

## Fonte de linguagens populares

Para RQ05 e RQ07, o projeto usa uma unica referencia:

- Fonte: GitHub Octoverse 2025
- URL: https://octoverse.github.com/
- Arquivo: `github_ingest/config/popular_languages.json`

A classificacao `is_popular_language` usa as linguagens definidas nesse arquivo.

## 1. Configurar ambiente Python

```bash
cd lab-medicao/github_ingest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `github_ingest/.env` e coloque seu PAT do GitHub:

```env
GITHUB_TOKEN=github_pat_seu_token_aqui
```

## 2. Configurar o profile do dbt

Copie o exemplo para `~/.dbt/profiles.yml`, ou adapte seu arquivo existente:

```bash
mkdir -p ~/.dbt
cp profiles.example.yml ~/.dbt/profiles.yml
```

O profile deve apontar para o mesmo DuckDB usado pela ingestao. Se voce sempre roda `dbt` a partir da raiz do projeto, pode usar caminho relativo:

```yaml
lab_medicao:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: github_ingest/data/github.duckdb
```

## 3. Rodar a ingestao

Coleta padrao dos 1.000 repositorios com mais estrelas:

```bash
cd lab-medicao/github_ingest
source .venv/bin/activate
python ingest_github.py
```

Se a coleta parar por rate limit ou interrupcao, rode o mesmo comando novamente. O script usa checkpoint e pula repositorios ja coletados.

Para refazer a coleta do zero:

```bash
python ingest_github.py --no-resume
```

## 4. Rodar dbt

```bash
cd lab-medicao
dbt run --select staging.github gold.github
dbt test --select staging.github gold.github
```

As tabelas finais ficam no DuckDB:

- `gold_rq05_popular_languages`
- `gold_rq06_closed_issues`
- `gold_rq07_popular_language_comparison`

## 5. Abrir DuckDB UI

Feche o dbt antes de abrir a UI, porque DuckDB usa lock no arquivo.

```bash
cd lab-medicao/github_ingest
duckdb -ui data/github.duckdb
```

Quando a UI estiver aberta, voce pode consultar:

```sql
select * from gold_rq05_popular_languages;
select * from gold_rq06_closed_issues;
select * from gold_rq07_popular_language_comparison;
```

## 6. Preparar para subir no remoto

Inicialize o Git se ainda nao existir:

```bash
cd lab-medicao
git init
git status --short
```

Confira que `.env`, `.duckdb`, `.venv`, `target/` e `logs/` nao aparecem como arquivos a commitar. O Parquet `github_ingest/data/parquet/repositories.parquet` deve aparecer porque e entregue junto com o projeto.

Depois:

```bash
git add .
git commit -m "Add GitHub mining pipeline with dbt gold tables"
git remote add origin URL_DO_REPOSITORIO_REMOTO
git branch -M main
git push -u origin main
```
