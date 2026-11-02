# Lab04 — testes de hipótese para falhas de CI (P4)

## Cenário e registro prévio à simulação

**Pergunta:** a taxa de falha do CI do projeto Ruff excede a meta de 5%?

- **Par P4:** teste Z para uma proporção × teste binomial exato.
- **Unidade de análise:** uma execução concluída do workflow `CI`, acionada por `push` em `main`, por commit. Uma falha é `conclusion = failure`; um sucesso é `conclusion = success`.
- **H₀:** a probabilidade de falha é no máximo 5% (`p ≤ 0,05`). Para calcular os p-valores, usamos a fronteira `p₀ = 0,05`.
- **H₁:** a probabilidade de falha é maior que 5% (`p > 0,05`). Ambos os testes são unicaudais à direita, com `α = 0,05`.
- **Expectativa registrada antes de simular:** o binomial exato deve controlar melhor o erro tipo I com `n = 30`. Sob H₀, a contagem esperada de falhas é `n × p₀ = 1,5`, pequena para a aproximação normal usada pelo Z. O teste Z pode ter mais poder aparente se rejeitar mais vezes sob H₀, mas isso não seria uma vantagem válida. As simulações das próximas US verificarão a expectativa.

O Z usará a variância **sob H₀**, `p₀(1−p₀)/n`, e o binomial usará a cauda superior exata. A escolha dos testes não depende do resultado observado na amostra. A pergunta avalia uma **meta**, não uma comparação entre dois grupos.

## Amostra real e coleta

Fonte: [workflow CI do `astral-sh/ruff`](https://github.com/astral-sh/ruff/actions/workflows/ci.yaml) via [API de workflow runs do GitHub](https://docs.github.com/en/rest/actions/workflow-runs). O workflow tem ID `32130301`. O arquivo versionado [`data/raw/ci_runs.csv`](data/raw/ci_runs.csv) contém as 30 execuções elegíveis mais recentes com `created_at ≤ 2026-11-02T18:14:10Z`, filtradas por `event=push`, `branch=main`, `status=completed` e conclusão `success` ou `failure`. Execuções do mesmo commit são deduplicadas por `head_sha`. A seleção é feita por data e ID, **antes** de contar falhas, e cada linha inclui o link da execução para auditoria.

Há **30 execuções, 5 falhas e 25 sucessos** (`5/30 = 16,67%`) entre `2026-10-30T22:03:25Z` e `2026-11-02T18:14:10Z`. A variável é binária: 25 zeros e 5 uns; portanto, é assimétrica e não tem outliers numéricos no sentido usual. Um cluster de falhas causado pela mesma mudança ou infraestrutura pode violar a independência entre execuções; além disso, a amostra cobre um intervalo curto e não representa automaticamente o histórico do projeto.

| Coluna do CSV | Significado |
| --- | --- |
| `repository`, `workflow_id` | Fonte e workflow fixados pelo protocolo. |
| `run_id`, `run_attempt` | Identificação da execução e tentativa reportada pela API. |
| `head_sha` | Commit; deve ser único na amostra. |
| `event`, `head_branch`, `created_at` | Filtros e instante UTC de criação. |
| `conclusion` | `failure` ou `success`; origem da variável binária. |
| `html_url` | Link direto para conferir a execução. |

## Dados simulados planejados

O gerador da US #97 usará Bernoulli independente, com `numpy.random.default_rng(42)`: `n = 30`, `p₀ = 0,05` sob H₀. Para poder, a grade proposta é `p = 0,05; 0,075; 0,10; 0,15; 0,20; 0,30`, cobrindo a proporção real observada de aproximadamente 0,167. A situação adversa pode usar `n = 10`, tornando ainda pior a aproximação normal. A amostra real fundamenta o tamanho da amostra e a faixa de efeitos, mas **não** prova que as execuções sejam independentes nem fixa uma probabilidade verdadeira de falha.

## Reconstrução de CSV → Parquet → dbt

Da raiz do repositório, instale `requirements.txt` no ambiente virtual e execute:

```bash
python3 -m labs.lab04_ci
```

Esse único comando valida o CSV versionado, substitui a tabela `lab04_ci_runs` em `data/warehouse.duckdb`, exporta `data/parquet/ci_runs.parquet` e executa `dbt build` apenas para os modelos do Lab04. O dbt usa um perfil temporário que aponta para o DuckDB compartilhado. Não é preciso token nem acesso à rede para reconstruir os dados.

- `stg_lab04_ci_runs`: **view** com as 30 linhas e a coluna binária `failed`.
- `gold_lab04_ci_failure_rate`: tabela com contagem, falhas, proporção e intervalo de datas.
- O Parquet é versionado como no Lab02; o arquivo DuckDB é gerado localmente e ignorado pelo Git.

Para recoletar **a mesma janela fixa** pela API e atualizar o CSV antes da reconstrução, configure `GITHUB_TOKEN` e rode `python3 -m labs.lab04_ci --refresh`. O token nunca é salvo no CSV, no Parquet ou no cache. Se não houver 30 commits elegíveis dentro do alcance paginado da API, a coleta falha sem substituir o CSV. A API pode mostrar um resultado diferente após uma nova tentativa de workflow; por isso, o CSV versionado é a referência reprodutível do estudo.

## Continuação do laboratório

Esta entrega cobre a US #96: cenário, hipóteses, dados reais, Parquet e visão dbt. A US #97 implementa o gerador, os dois testes em um conjunto simulado e G1/G2 em conjunto com a #98. As 10.000 repetições de Q1/Q2 pertencem à #99; a aplicação final dos testes à amostra real e a recomendação pertencem à #102.
