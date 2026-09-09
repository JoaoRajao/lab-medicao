# Lab02 - Assistentes de IA vs codificacao manual

Preparacao da Sprint 1 do experimento controlado em Python.

## Estrutura

```text
lab02/
  katas/                    # 6 katas com testes pytest de aceitacao
  scripts/
    run_trial_timer.py       # Registra tempo e resultado de testes por trial
    collect_static_metrics.py # Coleta Radon e jscpd
    ingest_trials_to_parquet.py
  data/
    raw/trials_sample.jsonl  # Dados de exemplo para validar dbt
    parquet/trials.parquet   # Parquet de exemplo consumido pelo dbt
```

## Validar preparacao

Instale as dependencias Python:

```bash
pip install -r github_ingest/requirements.txt
```

Colete os testes dos katas:

```bash
python3 -m pytest --collect-only lab02/katas
```

Gere o Parquet de exemplo:

```bash
python3 lab02/scripts/ingest_trials_to_parquet.py \
  --input lab02/data/raw/trials_sample.jsonl \
  --output lab02/data/parquet/trials.parquet
```

Rode o dbt:

```bash
DBT_PROFILES_DIR=.tmp_dbt_profiles dbt run --select staging.lab02 gold.lab02
DBT_PROFILES_DIR=.tmp_dbt_profiles dbt test --select staging.lab02 gold.lab02
```

## Executar um trial real

```bash
python3 lab02/scripts/run_trial_timer.py \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual
```

Para metricas estaticas:

```bash
python3 lab02/scripts/collect_static_metrics.py \
  --trial-id P1-warehouse_batches-manual \
  --participant P1 \
  --kata warehouse_batches \
  --treatment manual \
  --solution-path lab02/katas/warehouse_batches/solution.py
```

Duplicacao usa `jscpd` via `npx` quando disponivel.
