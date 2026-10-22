# Replicacao do pipeline (Lab03, entrega final)

`amostra_30.csv` e a subamostra fixa para replicacao: `dataset.sample(n=30, random_state=42)` sobre
`labs/lab03_dora/data/dataset.csv`. O passo a passo para o grupo replicador esta no
[README do lab](../README.md#para-o-grupo-replicador).

## Autorreplicacao (22/10/2026)

Antes de entregar o pipeline, o proprio grupo executou o roteiro do replicador, so com o README e com o
cache vazio:

```bash
python -m labs.lab03_dora --config labs/lab03_dora/config.yaml \
  --repositorios labs/lab03_dora/replicacao/amostra_30.csv \
  --saida labs/lab03_dora/replicacao/autorreplicacao
python -m labs.lab03_dora.comparar_datasets \
  --original labs/lab03_dora/data/dataset.csv \
  --replicado labs/lab03_dora/replicacao/autorreplicacao/dataset.csv
```

| Resultado | Valor |
| --- | --- |
| Execucao | concluida sem intervencao, cerca de 1h20, 8.593 requisicoes |
| Repositorios incluidos | 30 de 30 |
| Metricas identicas ao original | 6 de 6 (frequencia, lead time a/b, CFR a/b, recuperacao) |
| Mesma categoria DORA | 30 de 30 (100%) |
| Variaveis que mudaram | estrelas (30 repositorios) e contribuidores (24), medidas na data da coleta |

Os CSVs da execucao estao em `autorreplicacao/`; `comparacao_metricas.csv` e
`comparacao_por_repositorio.csv` guardam a comparacao. O cache e os CSVs brutos (`release_commits.csv`,
`workflow_runs.csv`) ficam fora do Git.
