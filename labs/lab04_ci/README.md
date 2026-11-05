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

## Dados simulados e aplicação dos testes (US #97)

O módulo `labs.lab04_ci.simulacao` implementa o gerador reprodutível e a aplicação simultânea dos dois testes do par P4:

- **Gerador Bernoulli independente:** utiliza `numpy.random.default_rng(42)` para gerar sequências de execuções (1 = falha, 0 = sucesso). Permite simular sob $H_0$ ($p_0 = 0{,}05$) e sob efeitos ($p = 0{,}075; 0{,}10; 0{,}15; 0{,}167; 0{,}20; 0{,}30$), além de situações com amostras pequenas ($n = 10$).
- **Aplicação dos testes:**
  - `aplicar_teste_z`: calcula a estatística $z$ com variância sob $H_0$, $p$-valor unicaudal e decisão ($\alpha = 0{,}05$).
  - `aplicar_teste_binomial`: calcula o $p$-valor exato via distribuição binomial cumulativa à direita $P(X \ge k)$ e decisão.
  - `comparar_testes`: executa ambos sobre o mesmo conjunto simulado ou contagem, avaliando concordância e gerando explicação textual interpretada.
- **Suporte à S02 (10.000 repetições):** funções vetorizadas `simular_repeticoes_z` e `simular_repeticoes_binomial` calculam estatísticas e decisões para arrays inteiros de contagens sem overhead de laços em Python.

Para executar a demonstração interpretada dos cenários via terminal:

```bash
python3 -m labs.lab04_ci.simulacao
```

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

## Dashboard

**Publicado em:** <https://joaorajao-lab-medicao-labslab04-ciapp-jw2ure.streamlit.app/> (Streamlit Community Cloud, atualizado a cada push na `master`). O deploy instala só [`requirements.txt`](requirements.txt) desta pasta, com as dependências do dashboard.

Para rodar localmente, da raiz do repositório, com o `requirements.txt` instalado:

```bash
streamlit run labs/lab04_ci/app.py
```

O dashboard abre no navegador (padrão `http://localhost:8501`) e lê só o CSV versionado: não precisa de token nem de rede. Na S01 ele traz as três primeiras seções exigidas pelo enunciado (#98):

| Seção | Conteúdo |
| --- | --- |
| 1. Cenário | Pergunta, H₀ e H₁ (unicaudais à direita, α = 0,05), origem e tamanho da amostra real, expectativa registrada antes de simular. |
| 2. Os dados (G1) | Sucessos e falhas reais ao lado de duas amostras simuladas de 30 execuções (Bernoulli, semente 42): sob H₀ (p = 0,05) e com a taxa observada (p ≈ 0,167). |
| 3. Como os testes funcionam (G2) | Distribuição de cada estatística sob H₀, região de rejeição sombreada e p-valor da amostra real marcado como área. Um botão muda o eixo vertical para escala logarítmica e mostra a cauda. No painel do Z, os valores possíveis de z sob H₀ (X é discreto) aparecem sobre a normal assumida: na cauda, eles ficam acima da curva, por isso o Z é liberal. Abaixo, uma tabela compara os dois testes. |

Cada gráfico vem com um texto de 2 a 4 frases, montado a partir dos dados (`textos.py`), e cada teste tem sempre a mesma cor: **Z em azul** e **binomial em laranja**. Os gráficos são interativos (Plotly, com valores ao passar o mouse) e usam uma paleta validada para daltonismo (`graficos.py`). O topo traz os links, os indicadores da amostra e os p-valores; a barra lateral tem o índice das sete seções. As contas do G2 estão em `estatistica.py`. Com n = 30, o Z rejeita H₀ a partir de 4 falhas, o que acontece com probabilidade real de 6,1% sob H₀, e o binomial a partir de 5, com 1,6%.

A amostra simulada do G1 consome o gerador reprodutivo definitivo (`estatistica.amostra_simulada` delegando para `simulacao.gerar_amostra`).

## Continuação do laboratório

Esta entrega cobre as US #96 (cenário, hipóteses, dados reais, Parquet e dbt), #98 (dashboard com G1 e G2) e #97 (gerador reprodutível, testes Z e Binomial e vetorização para repetidores). As 10.000 repetições de Q1/Q2 pertencem à #99; a aplicação final dos testes à amostra real e a recomendação pertencem à #102.
