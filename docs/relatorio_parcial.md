# Relatorio Parcial - Lab01 (S01 + S02)

Primeira versao do relatorio, conforme entregavel da Lab01S02. Documento vivo: sera completado nas proximas sprints com os itens ainda pendentes, marcados como TODO.

## 1. Introducao

Este laboratorio estuda caracteristicas de repositorios populares open-source no GitHub, coletando dados dos 1.000 repositorios com mais estrelas para responder sete questoes de pesquisa (RQ01 a RQ07). Em paralelo, o grupo estruturou um GitHub Projects (v2) para acompanhar o proprio processo de trabalho ao longo do semestre.

Hipoteses informais iniciais do grupo, antes da analise dos dados:

- **RQ01 (idade):** repositorios populares tendem a ser maduros, levando anos para acumular a visibilidade que tem hoje.
- **RQ02 (PRs aceitas):** repositorios populares recebem contribuicao externa significativa, dado o alcance da comunidade.
- **RQ03 (releases):** repositorios populares lancam releases com regularidade, como parte de um processo de manutencao ativo.
- **RQ04 (atualizacao):** repositorios populares sao atualizados com frequencia, refletindo manutencao continua.
- **RQ05 (linguagem popular):** repositorios populares tendem a concentrar-se nas linguagens mais populares do mercado.
- **RQ06 (issues fechadas):** repositorios populares mantêm alto percentual de issues fechadas, por terem processos de triagem mais maduros.
- **RQ07 (linguagem x atividade):** repositorios em linguagens populares recebem mais contribuicao, lancam mais releases e sao atualizados com mais frequencia que os demais.

## 2. Metodologia de coleta

- Coleta via API GraphQL do GitHub, usando query e script proprios do grupo (`github_ingest/ingest_github.py`), sem bibliotecas de terceiros para consumir a API.
- Paginacao por cursor (`after`/`hasNextPage`) buscando ate 1.000 repositorios ordenados por estrelas (`stars:>1000 archived:false fork:false sort:stars-desc`).
- Saidas geradas: DuckDB (`github_ingest/data/github.duckdb`), Parquet (`github_ingest/data/parquet/repositories.parquet`) e CSV (`github_ingest/data/csv/repositories.csv`).
- Modelagem em camadas via dbt: staging (`stg_github_repositories`) e gold (uma tabela por RQ, `models/gold/github/`), com testes `not_null`/`unique` e testes de consistencia especificos para RQ05-07.
- Fonte de referencia para "linguagens populares" (RQ05 e RQ07): GitHub Octoverse 2025 (`github_ingest/config/popular_languages.json`), mantida constante em todo o laboratorio.

## 3. Resultados por RQ

### RQ01 - Idade dos repositorios (`gold_rq01_age`)

| Repositorios | Media (dias) | Mediana (dias) | Minimo (dias) | Maximo (dias) |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 2792,27 | 2819,00 | 0 | 6698 |

**Hipotese informal / discussao:** pendente — issue [#6](https://github.com/JoaoRajao/lab-medicao/issues/6) (responsavel: Salomao0tavio).

### RQ02 - Pull requests aceitas (`gold_rq02_pull_requests`)

| Repositorios | Media | Mediana | Minimo | Maximo |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 4317,65 | 798,00 | 0 | 103013 |

**Hipotese informal / discussao:** pendente — issue [#6](https://github.com/JoaoRajao/lab-medicao/issues/6) (responsavel: Salomao0tavio).

### RQ03 - Releases (`gold_rq03_releases`)

| Repositorios | Media | Mediana | Minimo | Maximo |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 129,34 | 42,00 | 0 | 1000 |

**Hipotese informal / discussao:** pendente — issue [#7](https://github.com/JoaoRajao/lab-medicao/issues/7) (responsavel: Salomao0tavio).

### RQ04 - Dias desde a ultima atualizacao (`gold_rq04_updates`)

| Repositorios | Media (dias) | Mediana (dias) | Minimo (dias) | Maximo (dias) |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 99,02 | 1,00 | 0 | 2445 |

**Hipotese informal / discussao:** pendente — issue [#7](https://github.com/JoaoRajao/lab-medicao/issues/7) (responsavel: Salomao0tavio).

### RQ05, RQ06 e RQ07

Validacao completa, com distribuicoes, outliers e hipoteses informais, ja documentada em [`docs/rq05_rq07_validacao.md`](rq05_rq07_validacao.md) (issue [#8](https://github.com/JoaoRajao/lab-medicao/issues/8), status no board: Review).

Resumo:

- **RQ05:** 59,8% dos repositorios estao em linguagens classificadas como populares pela fonte adotada (Octoverse 2025); hipotese apoiada parcialmente.
- **RQ06:** mediana de 87,54% de issues fechadas; hipotese de alto percentual de fechamento apoiada pelos dados.
- **RQ07:** grupo de linguagens populares apresenta mediana maior de PRs aceitas, mediana maior de releases e mediana menor de dias desde a ultima atualizacao; hipotese apoiada de forma moderada, com excecoes relevantes (Go, Rust).

## 4. Configuracao do processo

- **GitHub Projects (v2):** [`@JoaoRajao's KANBAN TEST`](https://github.com/users/JoaoRajao/projects/4), vinculado ao repositorio `JoaoRajao/lab-medicao`.
- **Cartoes:** issues reais do repositorio (sem draft issues soltas), cada uma com um responsavel (campo Assignee).
- **Colunas do board (Status):** Backlog, To Do, Doing, Review, Done.
- **Limite de WIP (coluna Doing): 3.** Justificativa: o grupo e um trio: com WIP = numero de integrantes, cada pessoa mantem no maximo uma tarefa em andamento por vez, evitando multitasking e incentivando terminar (mover para Review/Done) antes de puxar a proxima issue do To Do.
- **Snapshots de fechamento de sprint:** script proprio (`github_ingest/export_project_snapshot.py`), reaproveitando a query GraphQL da Parte 1, exportando itens + status atual para CSV a cada sprint (`github_ingest/data/project_snapshots/`). Snapshots disponiveis ate o momento:
  - `snapshot_Lab01S01_2026-08-14.csv`
  - `snapshot_Lab01S02_2026-08-20.csv`

## 5. Pendencias para a proxima versao

- Hipoteses informais de RQ01 e RQ02 (issue [#6](https://github.com/JoaoRajao/lab-medicao/issues/6)).
- Hipoteses informais de RQ03 e RQ04 (issue [#7](https://github.com/JoaoRajao/lab-medicao/issues/7)).
- Mover a issue [#8](https://github.com/JoaoRajao/lab-medicao/issues/8) de "Review" para "Done" no board (trabalho ja mergeado via PR #19).
- Analise e visualizacao de dados das 7 RQs (Lab01S03, issues [#10](https://github.com/JoaoRajao/lab-medicao/issues/10)-[#12](https://github.com/JoaoRajao/lab-medicao/issues/12)).
- Print do board para anexar ao relatorio final.
