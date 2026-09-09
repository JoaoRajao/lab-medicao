# Lab02S01 - Desenho e preparacao do experimento

## Objetivo

Avaliar, por meio de um experimento controlado, o impacto do uso de assistente de IA na resolucao de tarefas de programacao em Python. O estudo compara o tratamento com ChatGPT contra codificacao manual em relacao a tempo de resolucao, defeitos funcionais e qualidade estrutural do codigo.

## Questoes de pesquisa e hipoteses

| RQ | Questao | Hipotese nula | Hipotese alternativa |
| --- | --- | --- | --- |
| RQ1 | O uso de assistente de IA reduz o tempo necessario para resolver uma tarefa? | Nao ha diferenca na mediana do tempo ate passar nos testes entre os tratamentos. | O tratamento com ChatGPT reduz a mediana do tempo ate passar nos testes. |
| RQ2 | O uso de assistente de IA reduz a quantidade de defeitos? | Nao ha diferenca na taxa de testes passando ao final do time-box. | O tratamento com ChatGPT aumenta a taxa de testes passando e reduz testes falhando. |
| RQ3 | O uso de assistente de IA altera complexidade ou duplicacao? | Nao ha diferenca nas metricas estaticas entre tratamentos. | O tratamento com ChatGPT altera complexidade ciclomática, duplicacao, LOC ou indice de manutenibilidade. |

## Variaveis

Variavel independente:

- Tratamento: `ai_assisted` ou `manual`.

Variaveis dependentes:

- `time_to_green_seconds`: tempo ate todos os testes de aceitacao passarem.
- `censored`: indica trial encerrado no time-box sem sucesso.
- `tests_passed`, `tests_failed`, `acceptance_success_rate`.
- `cyclomatic_complexity_avg`, `maintainability_index`, `loc`.
- `duplication_pct`.

Variaveis de controle:

- Linguagem: Python.
- Assistente de IA: ChatGPT.
- Time-box: 35 minutos por trial.
- Suite de testes: pytest.
- Metricas estaticas: Radon e jscpd.

## Desenho experimental

O desenho recomendado e crossover/within-subject contrabalanceado. Cada integrante resolve os mesmos 6 katas, metade com ChatGPT e metade sem assistente. A ordem alterna por participante para reduzir efeito de aprendizado.

| Participante | Ordem proposta |
| --- | --- |
| P1 | K1 manual, K2 ai_assisted, K3 manual, K4 ai_assisted, K5 manual, K6 ai_assisted |
| P2 | K1 ai_assisted, K2 manual, K3 ai_assisted, K4 manual, K5 ai_assisted, K6 manual |
| P3 | K1 manual, K2 ai_assisted, K3 ai_assisted, K4 manual, K5 manual, K6 ai_assisted |

Trials que nao passam em todos os testes dentro de 35 minutos devem ser registrados como censurados em 2.100 segundos, nao descartados.

## Katas escolhidos

| Codigo | Kata | Descricao |
| --- | --- | --- |
| K1 | `warehouse_batches` | Consolidar lotes por produto, validade e prioridade. |
| K2 | `route_reconciliation` | Reconciliar rotas planejadas e executadas. |
| K3 | `invoice_window` | Calcular janelas de cobranca, descontos e atrasos. |
| K4 | `sensor_anomaly` | Detectar anomalias simples em leituras sequenciais. |
| K5 | `support_queue` | Priorizar fila de suporte por SLA e severidade. |
| K6 | `dependency_unlock` | Resolver ordem de desbloqueio de tarefas com dependencias. |

Os katas foram definidos de forma autoral e com entrada/saida deterministica para reduzir risco de memorizacao por ferramentas treinadas em exercicios muito conhecidos.

## Preparacao tecnica

Estrutura preparada:

- `lab02/katas/`: enunciados, placeholders e testes de aceitacao.
- `lab02/scripts/run_trial_timer.py`: cronometro e registro de resultados do trial.
- `lab02/scripts/collect_static_metrics.py`: coleta Radon e jscpd.
- `lab02/scripts/ingest_trials_to_parquet.py`: conversao de registros JSONL/CSV para Parquet.
- `models/staging/lab02/`: staging dbt dos trials.
- `models/gold/lab02/`: agregacoes para RQ1, RQ2 e RQ3.

## Ameacas a validade

| Ameaca | Impacto | Mitigacao |
| --- | --- | --- |
| Efeito de aprendizado | Resolver um kata pode facilitar os seguintes. | Usar ordem contrabalanceada entre participantes. |
| Familiaridade previa com ChatGPT | Participantes mais experientes podem ganhar vantagem. | Registrar tratamento e participante para analise pareada. |
| Memorizacao de katas conhecidos | O assistente pode reproduzir solucoes vistas no treinamento. | Usar katas autorais e pouco indexados. |
| Variacao de dificuldade entre katas | Diferenças de tarefa podem mascarar efeito do tratamento. | Usar 6 katas pequenos/medios e comparar por participante/tratamento. |
| Pressao do time-box | Trials incompletos podem enviesar a media. | Registrar censura em 35 minutos e usar mediana/IQR. |

## Comandos de validacao da preparacao

```bash
python3 -m pytest --collect-only lab02/katas
python3 -m py_compile lab02/scripts/*.py
python3 lab02/scripts/ingest_trials_to_parquet.py --input lab02/data/raw/trials_sample.jsonl --output lab02/data/parquet/trials.parquet
DBT_PROFILES_DIR=.tmp_dbt_profiles dbt run --select staging.lab02 gold.lab02
DBT_PROFILES_DIR=.tmp_dbt_profiles dbt test --select staging.lab02 gold.lab02
```
