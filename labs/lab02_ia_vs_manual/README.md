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

O cronometro funciona em tres etapas -- `start` marca o inicio real da tentativa, `check` roda os
testes quantas vezes quiser sem parar o relogio, e `stop` encerra o cronometro e grava o registro
com o tempo decorrido de verdade (nao o tempo de execucao do `pytest`, que e quase instantaneo):

```bash
python -m labs.lab02_ia_vs_manual.scripts.run_trial_timer start \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual

# ... escreva a solucao em labs/lab02_ia_vs_manual/katas/warehouse_batches/solution.py ...

python -m labs.lab02_ia_vs_manual.scripts.run_trial_timer check \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual

python -m labs.lab02_ia_vs_manual.scripts.run_trial_timer stop \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual
```

Para trials `ai_assisted`, passe `--assistant "<nome>"` no `start` (ex.: `--assistant "Claude Code"`);
sem isso o padrao e `"ChatGPT"`, so para nao quebrar registros antigos.

O `stop` grava em `labs/lab02_ia_vs_manual/data/raw/trials.jsonl` (tempo real, testes passando/
falhando, censura se o time-box de 35 min (2100s) for atingido sem sucesso). Depois, para metricas
estaticas do mesmo trial:

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
