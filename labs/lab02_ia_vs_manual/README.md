# Lab02 - Assistentes de IA vs codificacao manual

Experimento controlado (crossover within-subject) comparando resolucao de katas em Python com e
sem assistente de IA (ChatGPT). Sprint 1: desenho do experimento + preparacao (katas, cronometragem,
metricas estaticas, pipeline dbt).

Todos os comandos abaixo rodam a partir da raiz do repositorio, com o ambiente da raiz ativado
(`pip install -r requirements.txt`, ver README raiz).

## Estrutura

```text
labs/lab02_ia_vs_manual/
  katas/                        # 6 katas autorais com testes pytest de aceitacao
  scripts/
    run_trial_timer.py           # Cronometra um trial (time-to-green, censura em 35 min)
    collect_static_metrics.py    # Coleta Radon (cc/raw/mi) e jscpd (duplicacao)
    ingest_trials_to_parquet.py  # Converte JSONL/CSV de trials para o warehouse + Parquet
  data/
    raw/trials_sample.jsonl      # Dados de exemplo para validar o pipeline dbt
    parquet/trials.parquet       # Parquet gerado a partir da tabela lab02_trials
```

A tabela `lab02_trials` fica no warehouse compartilhado (`data/warehouse.duckdb`), como qualquer
outro lab -- ver `shared/warehouse.py` no README raiz.

## Dependencias

`pytest` e `radon` ja fazem parte do `requirements.txt` da raiz (`pip install -r requirements.txt`).
Nao ha requirements.txt proprio deste lab -- mesma convencao do resto do repositorio.

Duplicacao de codigo usa `jscpd` via `npx` (Node.js). Nao ha instalacao previa necessaria alem de
ter Node/npx disponivel -- `npx --yes jscpd ...` baixa sob demanda. Se `npx` nao estiver disponivel,
`collect_static_metrics.py` grava `duplication_pct` como `null` em vez de falhar.

## Validar a preparacao (dados de exemplo)

Colete os testes dos katas (devem coletar, mas falhar -- `solution.py` e um stub `NotImplementedError`
ate o trial real ser executado na Sprint 2):

```bash
python -m pytest --collect-only labs/lab02_ia_vs_manual/katas
```

Gere o warehouse + Parquet de exemplo a partir dos dados sinteticos:

```bash
python -m labs.lab02_ia_vs_manual.scripts.ingest_trials_to_parquet \
  --input labs/lab02_ia_vs_manual/data/raw/trials_sample.jsonl \
  --output labs/lab02_ia_vs_manual/data/parquet/trials.parquet
```

Rode o dbt:

```bash
dbt run --select staging.lab02 gold.lab02
dbt test --select staging.lab02 gold.lab02
```

## Executar um trial real (Sprint 2)

```bash
python -m labs.lab02_ia_vs_manual.scripts.run_trial_timer \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual
```

Isso grava em `labs/lab02_ia_vs_manual/data/raw/trials.jsonl` (tempo, testes passando/falhando,
censura no time-box de 35 min). Depois, para metricas estaticas do mesmo trial:

```bash
python -m labs.lab02_ia_vs_manual.scripts.collect_static_metrics \
  --trial-id P1-warehouse_batches-manual \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual \
  --solution-path labs/lab02_ia_vs_manual/katas/warehouse_batches/solution.py
```

Depois de coletar os trials reais, junte os dois JSONL (tempo + metricas estaticas) num so registro
por trial e rode `ingest_trials_to_parquet.py` de novo apontando para o arquivo consolidado, antes de
rodar `dbt run`/`dbt test` para atualizar as tabelas gold.

## Orquestracao diaria com Airflow

O ambiente em `docker-compose.yml` usa Airflow 3.3.1 com LocalExecutor e PostgreSQL para os
metadados. A interface fica em <http://localhost:8080> e, no ambiente local, o usuario e senha
padrao sao `airflow` / `airflow`.

Inicialize e suba os servicos a partir da raiz:

```bash
docker compose build
docker compose up airflow-init
docker compose up -d
```

Em Linux, execute os comandos com `AIRFLOW_UID=$(id -u)` para que os logs criados pelo container
continuem pertencendo ao seu usuario. Para encerrar os servicos sem remover os metadados:

```bash
docker compose down
```

As DAGs ficam em `airflow/dags/lab02_pipeline.py`:

- `lab02_ingestion_daily`: roda todos os dias as 03:00 no fuso `America/Sao_Paulo` e publica o
  Parquet como um Asset do Airflow.
- `lab02_dbt_models`: e disparada quando o Asset e atualizado; roda os modelos e, em seguida, os
  testes dbt de `staging.lab02` e `gold.lab02`.

Por padrao, a ingestao usa `trials_sample.jsonl`. Para processar os trials reais, informe um caminho
visivel dentro do volume `/opt/airflow/project`, por exemplo:

```bash
LAB02_TRIALS_INPUT=/opt/airflow/project/labs/lab02_ia_vs_manual/data/raw/trials.jsonl \
  docker compose up -d
```

O Parquet e exportado para um arquivo temporario e substituido apenas depois de uma escrita bem
sucedida. Cada DAG permite somente uma execucao ativa, e todas as tarefas que acessam o warehouse
usam o pool `lab02_duckdb`, de uma vaga, para impedir escrita concorrente entre as duas DAGs. Feche
a DuckDB UI antes de executar o fluxo, pois ela pode manter um lock externo no warehouse.

```mermaid
flowchart LR
    CRON["Cron diario<br/>03:00 America/Sao_Paulo"] --> INGEST_DAG["DAG lab02_ingestion_daily"]
    INPUT["Trials JSONL ou CSV"] --> INGEST_DAG
    INGEST_DAG --> PYTHON["Ingestao Python"]
    PYTHON --> DB[("DuckDB<br/>lab02_trials")]
    PYTHON --> PARQUET["Parquet<br/>trials.parquet"]
    PARQUET --> ASSET["Asset do Airflow"]
    ASSET --> DBT_DAG["DAG lab02_dbt_models"]
    DBT_DAG --> STAGING["dbt staging.lab02"]
    STAGING --> GOLD["dbt gold.lab02"]
    GOLD --> TESTS["Testes dbt"]
    STAGING --> DB
    GOLD --> DB
```

O diagrama completo, incluindo os servicos internos do Airflow, PostgreSQL, camadas de dados e as
decisoes arquiteturais, esta em
[`docs/lab02/airflow_architecture.md`](../../docs/lab02/airflow_architecture.md).

Para diagnosticar o ambiente pela linha de comando:

```bash
docker compose run --rm airflow-cli dags list
docker compose run --rm airflow-cli dags list-import-errors
docker compose run --rm airflow-cli dags test lab02_ingestion_daily 2026-09-11
docker compose run --rm airflow-cli dags test lab02_dbt_models 2026-09-11
```

## Katas

| Kata | Descricao |
| --- | --- |
| `warehouse_batches` | Consolidar lotes por produto, validade e prioridade. |
| `route_reconciliation` | Reconciliar rotas planejadas e executadas. |
| `invoice_window` | Calcular janelas de cobranca, descontos e atrasos. |
| `sensor_anomaly` | Detectar anomalias simples em leituras sequenciais. |
| `support_queue` | Priorizar fila de suporte por SLA e severidade. |
| `dependency_unlock` | Resolver ordem de desbloqueio de tarefas com dependencias. |

Katas autorais e pouco indexados, para reduzir o risco de o assistente de IA reproduzir uma solucao
ja vista no treinamento em vez de efetivamente ajudar. Detalhes do desenho experimental (hipoteses,
variaveis, ordem contrabalanceada, ameacas a validade) em
[`docs/lab02/experiment_design.md`](../../docs/lab02/experiment_design.md).
