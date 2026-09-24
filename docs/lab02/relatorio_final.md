# Relatorio final - Lab02: assistentes de IA vs codificacao manual

Repositorio: https://github.com/JoaoRajao/lab-medicao
Quadro do grupo (GitHub Projects): https://github.com/users/JoaoRajao/projects/4

> Esqueleto. Trechos marcados com `A PREENCHER` dependem dos dados finais dos tres participantes.
> Nada abaixo de "Resultados" deve ser preenchido antes de `python -m labs.lab02_ia_vs_manual.analysis.dashboard`
> rodar sem avisos de validacao (sem marca d'agua PRELIMINAR).

## 1. Introducao

Experimento controlado (crossover within-subject, ordem contrabalanceada) que compara a resolucao de
katas em Python com e sem assistente de IA, em tempo, taxa de sucesso nos testes e qualidade estrutural
do codigo.

### Questoes de pesquisa e hipoteses

Fonte: `docs/lab02/experiment_design.md`.

| RQ | Questao | H0 | H1 |
| --- | --- | --- | --- |
| RQ1 | O assistente de IA reduz o tempo necessario para resolver uma tarefa? | Nao ha diferenca na mediana do tempo ate passar nos testes entre os tratamentos. | O tratamento com IA reduz a mediana do tempo ate passar nos testes. |
| RQ2 | O assistente de IA reduz a quantidade de defeitos? | Nao ha diferenca na taxa de testes passando ao final do time-box. | O tratamento com IA aumenta a taxa de testes passando e reduz testes falhando. |
| RQ3 | O assistente de IA altera complexidade ou duplicacao? | Nao ha diferenca nas metricas estaticas entre tratamentos. | O tratamento com IA altera complexidade ciclomatica, duplicacao, LOC ou indice de manutenibilidade. |

### Variaveis

- Independente: tratamento (`manual` ou `ai_assisted`).
- Dependentes: `time_to_green_seconds`, `censored`, `tests_passed`, `tests_failed`,
  `acceptance_success_rate`, `cyclomatic_complexity_avg`, `maintainability_index`, `loc`, `duplication_pct`.
- Controle: linguagem (Python), time-box (35 min), suite de testes (pytest), metricas estaticas (Radon, jscpd).

## 2. Metodologia

### 2.1 Participantes e desenho

Tres participantes resolvem os mesmos seis katas, metade com IA e metade sem, em ordem contrabalanceada:

| Participante | K1 | K2 | K3 | K4 | K5 | K6 |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | manual | ai_assisted | manual | ai_assisted | manual | ai_assisted |
| P2 | ai_assisted | manual | ai_assisted | manual | ai_assisted | manual |
| P3 | manual | ai_assisted | ai_assisted | manual | manual | ai_assisted |

### 2.2 Katas

Katas autorais, com testes de aceitacao em pytest (`labs/lab02_ia_vs_manual/katas/`):
K1 `warehouse_batches`, K2 `route_reconciliation`, K3 `invoice_window`, K4 `sensor_anomaly`,
K5 `support_queue`, K6 `dependency_unlock`. Validacao de dificuldade e indexacao:
`docs/lab02/katas_validacao.md` e `docs/lab02/kata_baselines.md`.

### 2.3 Ambiente e ferramentas

| Item | Valor |
| --- | --- |
| Linguagem | Python 3.14 |
| Testes | pytest 9.1.1 |
| Metricas estaticas | radon 6.0.1 (complexidade, LOC, manutenibilidade); jscpd via npx (duplicacao) |
| Armazenamento | DuckDB 1.5.5 + Parquet |
| Transformacao | dbt-duckdb 1.11.0 (`models/staging/lab02`, `models/gold/lab02`) |
| Analise e graficos | pandas 3.0.6, matplotlib 3.11.1 |
| Orquestracao | Airflow 3.3.1 (`airflow/`, `docs/lab02/airflow_architecture.md`) |

### 2.4 Assistente de IA

A PREENCHER: assistente e versao usados por participante nos trials `ai_assisted`. O desenho original
previa ChatGPT; os registros indicam Claude Code (P1) e, a confirmar, Gemini (P2). Registrar a versao
exata de cada um e tratar a diferenca em "Ameacas a validade".

### 2.5 Procedimento de coleta

1. `run_trial_timer.py start` marca o inicio real; `check` roda os testes sem parar o relogio;
   `stop` grava o tempo decorrido. Trial que nao fica verde em 35 min (2.100 s) e registrado como
   censurado, nunca descartado.
2. `collect_static_metrics.py` mede o `solution.py` do trial.
3. Um JSONL por participante em `labs/lab02_ia_vs_manual/data/raw/`, ingerido com
   `ingest_trials_to_parquet.py` e modelado no dbt.
4. Nos trials `manual`, a solucao e escrita pelo participante, sem sugestoes de IA.

### 2.6 Tratamento de dados e analise

- Consolidacao dos tres JSONL e validacao de integridade: `labs/lab02_ia_vs_manual/analysis/data.py`.
- Estatistica descritiva por mediana e IQR (N pequeno e assimetria); outliers pela regra do boxplot,
  documentados antes dos testes.
- Teste de Wilcoxon pareado (RQ1, RQ2, RQ3) e tamanho de efeito (Cliff's delta).
  A PREENCHER: nivel de significancia, decisao de pareamento e correcao para multiplos testes.

## 3. Resultados

> Figuras geradas por `python -m labs.lab02_ia_vs_manual.analysis.dashboard` em `docs/lab02/assets/`.

### 3.1 RQ1 - Tempo

![Tempo ate passar nos testes](assets/rq1_tempo_boxplot.png)
![Tempo por kata](assets/rq1_tempo_por_kata.png)

| Tratamento | n | Mediana (s) | Q1 | Q3 | Censurados |
| --- | --- | --- | --- | --- | --- |
| Manual | A PREENCHER | | | | |
| Com IA | A PREENCHER | | | | |

Wilcoxon: estatistica A PREENCHER, p = A PREENCHER, Cliff's delta = A PREENCHER.
Decisao sobre H0: A PREENCHER.

### 3.2 RQ2 - Taxa de sucesso e defeitos

![Trials com todos os testes passando](assets/rq2_sucesso.png)

| Tratamento | Trials verdes | Testes falhos (soma) | Mediana da taxa de sucesso |
| --- | --- | --- | --- |
| Manual | A PREENCHER | | |
| Com IA | A PREENCHER | | |

Wilcoxon: p = A PREENCHER, Cliff's delta = A PREENCHER. Decisao sobre H0: A PREENCHER.

### 3.3 RQ3 - Metricas estaticas

![Metricas estaticas](assets/rq3_metricas_boxplot.png)
![LOC x complexidade](assets/rq3_loc_vs_complexidade.png)
![Correlacao entre metricas](assets/correlacao_metricas.png)

| Metrica | Manual (mediana / IQR) | Com IA (mediana / IQR) | p | Cliff's delta |
| --- | --- | --- | --- | --- |
| Complexidade ciclomatica (media) | A PREENCHER | | | |
| Indice de manutenibilidade | A PREENCHER | | | |
| LOC | A PREENCHER | | | |
| Duplicacao (%) | A PREENCHER | | | |

### 3.4 Outliers e dados excluidos

A PREENCHER: outliers identificados (`analysis.stats.iqr_outliers`), tratamento adotado e trials
censurados. Nenhum trial e descartado sem registro aqui.

## 4. Discussao

A PREENCHER apos os resultados:

- RQ1 vs RQ2 vs RQ3: o ganho (ou nao) de tempo veio acompanhado de mais/menos defeitos e de codigo mais
  verboso ou mais complexo?
- A diferenca estrutural, se houver, e explicada por verbosidade (LOC) ou por complexidade real?
- Implicacoes praticas e limites da generalizacao (3 participantes, 6 katas pequenos).

## 5. Ameacas a validade

| Ameaca | Situacao neste experimento | Mitigacao / tratamento |
| --- | --- | --- |
| Efeito de aprendizado | Ordem alterna por participante. | Ordem contrabalanceada (secao 2.1). |
| Variacao de dificuldade entre katas | `dependency_unlock` saiu mais complexo que os demais (`docs/lab02/kata_baselines.md`). | Comparar dentro do mesmo kata (`rq1_tempo_por_kata.png`). |
| Memorizacao de katas conhecidos | Nenhum kata encontrado como problema indexado (`docs/lab02/katas_validacao.md`). | Katas autorais. |
| Amostra pequena | 3 participantes; o pareamento por participante rende so 3 pares, insuficiente para significancia no Wilcoxon exato. | A PREENCHER: pareamento por kata ou Mann-Whitney; reportar tamanho de efeito. |
| Assistente diferente do desenho | Desenho previa ChatGPT; foram usados outros assistentes (secao 2.4). | A PREENCHER: registrar por participante e discutir. |
| Familiaridade previa com IA | Nao medida. | Analise pareada por participante. |
| Instrumentacao do tempo | A primeira versao do cronometro media so a duracao do `pytest` (quase zero) e os stubs dos katas chegaram a ser sobrescritos pela solucao de referencia; corrigido nos PRs #47 e #44. | Trials afetados refeitos com o cronometro corrigido (issue #48). A PREENCHER: confirmar a substituicao dos dados. |

## 6. Conclusao

A PREENCHER: resposta objetiva a RQ1, RQ2 e RQ3 e proximos passos.

## 7. Reproducao

```bash
pip install -r requirements.txt
python -m pytest --collect-only labs/lab02_ia_vs_manual/katas
python -m labs.lab02_ia_vs_manual.scripts.run_trial_timer start --participant P1 --kata warehouse_batches --treatment manual
dbt run --select staging.lab02 gold.lab02
dbt test --select staging.lab02 gold.lab02
python -m labs.lab02_ia_vs_manual.analysis.dashboard
```

Snapshots do quadro: `data/kanban_snapshots/` (`Lab02S01`, `Lab02S02`, `Lab02S03` ao final).
