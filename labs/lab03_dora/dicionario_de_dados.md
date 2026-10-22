# Dicionario de dados - Lab03 (metricas DORA)

Documenta o `data/dataset.csv`, uma linha por repositorio da amostra final. O arquivo e gerado por
`python -m labs.lab03_dora.consolidacao --config labs/lab03_dora/config.yaml`, a partir dos CSVs das
etapas de coleta (sem chamar a API).

Convencoes:

- **Janela:** `janela.inicio` a `janela.fim` do `config.yaml` (2025-10-01 a 2026-09-30, 365 dias, 52,14 semanas).
- **Datas** em ISO 8601 UTC, como a API do GitHub devolve.
- **Celula vazia** significa "nao calculavel" (ex.: repositorio sem nenhum episodio de falha), nunca zero.
- **Release** = release publicada (`draft = false`) e que nao e pre-release (`prerelease = false`).
- **Run valido** = workflow run do default branch com `event = push` e `conclusion` em `success`, `failure`,
  `timed_out` ou `startup_failure`. As demais conclusoes sao ignoradas.

## Identificacao e caracteristicas (RQ 06)

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `repository` | texto | - | `full_name` da busca `GET /search/repositories?q=stars:A..B` |
| `stars` | inteiro | estrelas | `stargazers_count` da busca, no momento da coleta |
| `language` | texto | - | `language` da busca (linguagem principal segundo o GitHub); vazio se o GitHub nao detecta |
| `contributors` | inteiro | pessoas | Ultima pagina de `GET /repos/{r}/contributors?per_page=1&anon=true` (inclui anonimos); vazio quando a API recusa a contagem por a lista ser grande demais (HTTP 403) |
| `created_at` | data-hora | - | `created_at` da busca |
| `age_days` | inteiro | dias | `janela.fim - created_at` |
| `default_branch` | texto | - | `default_branch` da busca |

## Deploys e deployment frequency (RQ 01 e variantes da RQ 07)

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `releases_in_window` | inteiro | releases | Releases com `published_at` na janela (`GET /repos/{r}/releases`) |
| `pre_releases_in_window` | inteiro | releases | Releases com `prerelease = true` e `published_at` na janela |
| `tags_in_window` | inteiro | tags | Tags cujo commit apontado tem `authoredDate` na janela (GraphQL `refs(refPrefix: "refs/tags/")`) |
| `deployment_frequency_per_week` | decimal | releases/semana | `releases_in_window / (dias da janela / 7)` |
| `deployment_frequency_with_prereleases_per_week` | decimal | releases/semana | `(releases_in_window + pre_releases_in_window) / semanas da janela` (variante RQ 07) |
| `deployment_frequency_tags_per_week` | decimal | tags/semana | `tags_in_window / semanas da janela` (variante RQ 07) |

## Lead time for changes (RQ 02)

Para cada release R da janela, os commits incluidos vem de `GET /repos/{r}/compare/{anterior}...{R}`,
paginado ate o fim. A anterior e a release publicada imediatamente antes de R, mesmo fora da janela. A data
de um commit e `commit.author.date`.

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `releases_compared` | inteiro | releases | Releases com lead time calculado (tem anterior, compare ok e ao menos um commit com data) |
| `compare_404_count` | inteiro | releases | Releases ignoradas porque o compare devolveu 404 (tag apagada ou reescrita) |
| `releases_without_commits` | inteiro | releases | Releases sem commits novos em relacao a anterior (ficam fora das medianas) |
| `releases_diverged` | inteiro | releases | Compares com `status = diverged`: a anterior por data nao e ancestral de R (comum em branches de release). O compare conta os commits desde o ancestral comum; entram no calculo e sao contadas como ameaca a validade |
| `releases_incomplete_compare` | inteiro | releases | Releases em que o compare devolveu menos commits que o `total_commits` da API (paginacao de compares muito grandes); entram no calculo e sao contadas para auditoria |
| `lead_time_a_hours` | decimal | horas | Variante (a), por release: mediana, entre as releases, de `published_at(R) - data do commit mais antigo de R` |
| `lead_time_b_hours` | decimal | horas | Variante (b), por commit: mediana de `published_at(R) - data do commit` sobre todos os commits de todas as releases |

## Change failure rate (RQ 03)

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `workflow_runs_valid` | inteiro | runs | `successful_runs + failed_runs` |
| `successful_runs` | inteiro | runs | Runs validos com `conclusion = success` (`GET /repos/{r}/actions/runs?branch=..&event=push&created=..`, mes a mes) |
| `failed_runs` | inteiro | runs | Runs validos com `conclusion` em `failure`, `timed_out` ou `startup_failure` |
| `ignored_runs` | inteiro | runs | Runs de push no default branch com outras conclusoes (`cancelled`, `skipped`, em andamento...) |
| `cfr_a` | decimal | fracao (0 a 1) | Variante (a), proxy de CI: `failed_runs / workflow_runs_valid`, todos os workflows juntos |
| `cfr_b` | decimal | fracao (0 a 1) | Variante (b), proxy de entrega: `releases que falharam / releases avaliadas`; R falhou se uma release corretiva foi publicada ate 7 dias depois. Vem de `cfr_b_metrics.csv` (heuristica `semver-patch-commits-fix-v2`: patch do SemVer ou >= 1/3 dos commits com fix/revert/hotfix; F1 0,823 contra o consenso da amostra-ouro) |
| `cfr_b_releases_evaluated` | inteiro | releases | Denominador do `cfr_b` |
| `cfr_b_releases_censored` | inteiro | releases | Releases dos ultimos 7 dias da janela, fora do denominador (censura) |

## Tempo de recuperacao (RQ 04)

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `recovery_median_hours` | decimal | horas | Mediana dos episodios encerrados. Episodio: dentro de um mesmo workflow, da primeira falha apos um sucesso (`run_started_at`) ate o fim do proximo sucesso (`updated_at`) |
| `recovery_episodes` | inteiro | episodios | Episodios encerrados + censurados |
| `censored_episodes` | inteiro | episodios | Episodios sem sucesso posterior dentro da janela (censurados, nao descartados) |
| `censored_episode_ratio` | decimal | fracao (0 a 1) | `censored_episodes / recovery_episodes` |

## Classificacao DORA de referencia (combinacao C1 da RQ 07)

C1 usa release como deploy, lead time (a) e CFR (a). Cortes da secao 5 do enunciado:

| Metrica | Elite (4) | High (3) | Medium (2) | Low (1) |
| --- | --- | --- | --- | --- |
| Deployment frequency | >= 7/semana | >= 1 e < 7/semana | >= 1/mes e < 1/semana | < 1/mes |
| Lead time | < 1 dia | 1 dia a < 1 semana | 1 semana a < 30 dias | >= 30 dias |
| CFR | <= 15% | > 15% e <= 30% | > 30% e <= 45% | > 45% |
| Recuperacao | < 1 hora | 1 hora a < 1 dia | 1 dia a < 1 semana | >= 1 semana |

"1 por mes" em releases por semana e `7 / (365,25 / 12)`, cerca de 0,23.

| Coluna | Tipo | Unidade | Origem ou formula |
| --- | --- | --- | --- |
| `df_points` | inteiro 1-4 | pontos | Nota de `deployment_frequency_per_week` |
| `lead_time_points` | inteiro 1-4 | pontos | Nota de `lead_time_a_hours`; vazio se o lead time nao e calculavel |
| `cfr_points` | inteiro 1-4 | pontos | Nota de `cfr_a`; vazio se nao ha runs validos |
| `recovery_points` | inteiro 1-4 | pontos | Nota de `recovery_median_hours`; vazio se nao ha episodio encerrado |
| `dora_points` | inteiro 1-4 | pontos | Mediana das notas disponiveis, arredondada para baixo (ex.: 4, 3, 3, 1 -> 3) |
| `dora_category` | texto | - | `Elite`, `High`, `Medium` ou `Low`, conforme `dora_points` |
| `dora_metrics_used` | inteiro 0-4 | metricas | Quantas notas entraram na mediana. Com menos de 4, a classificacao usa so as metricas calculaveis |

## Arquivos de apoio

As colunas dos CSVs intermediarios (`repositories.csv`, `selection_*.csv`, `releases.csv`, `release_commits.csv`,
`tags.csv`, `pre_releases.csv`, `lead_time_metrics.csv`, `workflow_runs.csv`, `workflow_run_months.csv`,
`recovery_episodes.csv`, `workflow_metrics.csv`) estao descritas no [README do lab](README.md).
