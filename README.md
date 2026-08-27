# Laboratorio de Experimentacao de Software

Repositorio do grupo para os laboratorios da disciplina, com um pipeline analitico compartilhado
(Python + DuckDB + dbt) e um lab por pasta em `labs/`.

## Estrutura

```text
shared/                  # infra reaproveitavel entre labs (nao sabe o tema de nenhum lab)
  github_client.py        # transporte GraphQL puro (auth, retry, rate limit)
  pagination.py            # paginador generico por cursor
  warehouse.py              # leitura/escrita generica no DuckDB compartilhado
  checkpoint.py              # checkpoint JSONL generico para coletas longas
  kanban/
    export_project_snapshot.py  # roda toda sprint, de qualquer lab
  viz/
    charts.py                    # motor de grafico generico (paleta, mark specs)

data/
  warehouse.duckdb          # unico DuckDB do semestre (gitignored, regenerado a partir dos parquets)
  kanban_snapshots/         # CSVs de fechamento de sprint do GitHub Projects (semestre inteiro)

labs/
  lab01_repos_populares/    # Lab01: mineracao de repositorios populares do GitHub
    ingest.py                 # UNICO arquivo especifico: query GraphQL + schema + mapeamento
    visualize.py               # graficos especificos do Lab01
    config/, data/

models/
  staging/lab01/   gold/lab01/     # modelos dbt do Lab01 (um subdiretorio por lab)
tests/lab01/                        # testes de consistencia do Lab01
docs/lab01/                         # relatorios do Lab01
```

Cada lab novo segue o mesmo padrao: uma pasta em `labs/`, um subdiretorio homonimo em
`models/staging/`, `models/gold/`, `tests/` e `docs/`. Nenhum lab precisa alterar `shared/`.

## Labs

| Lab | Tema | Documentacao |
| --- | --- | --- |
| Lab01 | Mineracao de repositorios populares do GitHub (RQ01-RQ07) | [`labs/lab01_repos_populares/README.md`](labs/lab01_repos_populares/README.md), relatorios em [`docs/lab01/`](docs/lab01/) |

## Ambiente Python (unico para o repositorio inteiro)

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Isso instala `dbt-duckdb`, `duckdb`, `matplotlib` e `certifi` -- tudo que qualquer lab ou o dbt
precisam. Nao ha ambiente virtual por pasta.

## dbt

Copie o profile de exemplo (aponta para o warehouse compartilhado `data/warehouse.duckdb`):

```bash
mkdir -p ~/.dbt
cp profiles.example.yml ~/.dbt/profiles.yml
```

Rodar todos os modelos e testes do Lab01:

```bash
dbt run --select staging.lab01 gold.lab01
dbt test --select staging.lab01 gold.lab01
```

## GitHub Token (`.env` na raiz)

Tanto a ingestao de cada lab quanto o snapshot do Kanban usam o mesmo `GITHUB_TOKEN`, lido de um
`.env` **na raiz do repositorio** (nunca commitado):

```env
GITHUB_TOKEN=github_pat_seu_token_aqui
```

O token de ingestao (`labs/*/ingest.py`) precisa de acesso de leitura ao GitHub normal. O de
snapshot do Kanban (`shared/kanban/export_project_snapshot.py`) precisa do escopo `read:project`
(PAT classico) ou da permissao "Projects: Read" (fine-grained).

## Snapshot de fechamento de sprint (Kanban)

O GitHub Projects (v2) nao guarda historico de mudanca de coluna consultavel via API. Por isso, ao
final de cada sprint, qualquer lab pode rodar (a partir da raiz do repositorio):

```bash
python -m shared.kanban.export_project_snapshot --sprint Lab01S01
```

Gera `data/kanban_snapshots/snapshot_<sprint>_<data>.csv`. Esses CSVs sao versionados -- formam a
serie historica que serve de base para os labs de analise de processo.

## Dados que nao sobem para o Git

- `.env` (raiz)
- `.venv/`
- `data/*.duckdb` (warehouse, regenerado a partir dos parquets versionados)
- `labs/*/data/checkpoints/*.jsonl`
- `target/`, `logs/`

Os parquets/CSVs finais de cada lab (ex.: `labs/lab01_repos_populares/data/parquet/repositories.parquet`)
sobem para o repositorio para facilitar a avaliacao sem reprocessar a API.
