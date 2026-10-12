# Funil de selecao da amostra final (Lab03S02)

Gerado automaticamente pela etapa `selecao` do pipeline (`labs/lab03_dora/data/selection_funnel.csv` e
`selection_decisions.csv`), com a janela de 2025-10-01 a 2026-09-30. Serve de base para a secao de
Metodologia (#73).

| Etapa | Repositorios restantes | Descartados | Motivo do descarte |
| --- | ---: | ---: | --- |
| Candidatos examinados (`stars:>1000`, por faixas de estrelas) | 713 | - | - |
| Usam GitHub Actions | 643 | 70 | `total_count = 0` em `/actions/workflows` |
| >= 5 releases publicadas na janela | 346 | 297 | Menos de 5 releases (`draft = false`, sem pre-releases) |
| >= 50 workflow runs validos na janela | 300 | 46 | Menos de 50 runs `push` no default branch com conclusao de sucesso ou falha |
| Repositorio acessivel | 300 | 0 | Removido, bloqueado ou vazio |
| **Amostra final** | **300** | | |

## Como a busca percorre os candidatos

A busca `GET /search/repositories?q=stars:A..B` e fatiada por faixas de estrelas, das maiores para as
menores, e cada faixa com mais de 1.000 resultados e dividida ao meio ate caber no limite da API. Os
candidatos sao examinados nessa ordem e a busca para quando 300 repositorios passam por todos os
criterios (`amostra.repositorios` no `config.yaml`).

Consequencia: os 713 candidatos examinados sao os repositorios com mais estrelas do GitHub (de 40.865 a
552.497 estrelas), e a amostra final vai de 40.865 a 391.676 estrelas. O funil descreve esses candidatos,
nao todos os repositorios com mais de 1.000 estrelas. Isso deve aparecer nas ameacas a validade externa:
os resultados valem para os projetos open-source mais populares.

## Composicao da amostra final

Linguagens principais mais frequentes: TypeScript (80), Python (71), Go (32), Rust (31), JavaScript (29),
C++ (13), C (7) e Shell (6). Todos os 300 repositorios tem contagem de contribuidores.

## Reproducao

```bash
python -m labs.lab03_dora --config labs/lab03_dora/config.yaml --etapa selecao
```

Com o cache da coleta, o comando refaz o funil sem chamar a API. Numa coleta nova, os numeros podem
variar um pouco, porque as estrelas e as releases dos repositorios mudam com o tempo.
