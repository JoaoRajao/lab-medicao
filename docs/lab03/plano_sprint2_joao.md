# Plano de implementação — US atribuídas a João na Sprint 2 do Lab03

Base: `feature/sprint2`, criada a partir de `origin/master` em 14/10/2026 (`5709437`).
Escopo: issues abertas [#69](https://github.com/JoaoRajao/lab-medicao/issues/69),
[#70](https://github.com/JoaoRajao/lab-medicao/issues/70) e
[#71](https://github.com/JoaoRajao/lab-medicao/issues/71).

## Estado encontrado

- O sorteio e as planilhas já existem em `labs/lab03_dora/amostra_ouro/`: 60 repositórios e 300 releases (5 por repositório). `amostra_ouro.read_labels()` valida os rótulos preenchidos.
- `rotulagem_pedro.xlsx` está completa. `rotulagem_joao.xlsx` e `rotulagem_salomao.xlsx` ainda têm 0 de 60 rótulos de tipo de projeto, 0 de 60 de entregas reais e 0 de 300 de corretividade.
- #69 (avaliador 2) e #70 (avaliador 3) estão ambas atribuídas a João no GitHub. Pelos nomes das planilhas e pelo fato de #68 ser a rotulagem de Pedro, a distribuição esperada é João em #69 e Salomão em #70. Confirmar com o grupo e corrigir a atribuição de #70 no quadro; manter as três avaliações independentes.
- Ainda não há módulo de consenso, cálculo de kappa ou avaliação da heurística. A heurística de release corretiva e o CFR (b) pertencem à [#72](https://github.com/JoaoRajao/lab-medicao/issues/72), aberta e sem responsável atribuído; a etapa de avaliação da #71 depende da saída dela.
- `requirements.txt` ainda não inclui `statsmodels` e `scikit-learn`, necessários às funções exigidas pela #71.

## Ordem de execução

### 1. Rotulagem independente — #69 e #70

1. João preenche `rotulagem_joao.xlsx` sem consultar a planilha de Pedro, a de Salomão ou a saída da heurística. Para cada um dos 60 repositórios, classificar `tipo_projeto` e `entregas_reais`; para cada uma das 300 releases, classificar `corretiva`. Usar `observacoes` para decisões ambíguas e consultar os links, notas e commits já incluídos na planilha.
2. Salomão executa o mesmo protocolo em `rotulagem_salomao.xlsx` para a #70. Corrigir a atribuição da issue antes de tratá-la como trabalho de João concluído. Não copiar ou inferir os rótulos de outro avaliador.
3. Validar cada arquivo com `amostra_ouro.read_labels()`, conferir 60/300 linhas, chaves únicas e igualdade das chaves com os CSVs sorteados. Não executar `amostra_ouro.py --forcar`, pois isso sobrescreve os rótulos.
4. Commitar cada planilha em seu nome e fechar a respectiva issue somente quando todos os critérios estiverem satisfeitos.

### 2. Concordância e consenso — primeira parte da #71

1. Criar `labs/lab03_dora/validacao_amostra_ouro.py` para carregar as três planilhas com `read_labels()`, associar repositórios por `repositorio` e releases por `(repositorio, tag)`, rejeitar duplicatas, chaves ausentes e rótulos incompletos. A ordem das linhas não deve influenciar o resultado.
2. Calcular kappa de Fleiss separadamente para `tipo_projeto`, `entregas_reais` e `corretiva`, usando `statsmodels.stats.inter_rater.aggregate_raters` e `fleiss_kappa`. Registrar n, categorias, distribuição dos rótulos, valor de kappa e interpretação de Landis & Koch; a interpretação deve explicitar a convenção adotada e tratar valores negativos.
3. Aplicar maioria simples por item para gerar o consenso. Para empates 1–1–1 nas dimensões com três categorias ou mais, gravar a lista de casos pendentes e resolvê-los em reunião dos três avaliadores. Registrar a decisão e a justificativa, preservando os rótulos originais. Só gerar consenso final quando não houver pendências.
4. Produzir CSVs versionáveis em `labs/lab03_dora/amostra_ouro/` para consenso de repositórios, consenso de releases e relatório de divergências/desempates; documentar o protocolo e os resultados em `docs/lab03/validacao_amostra_ouro.md`.

### 3. Avaliação da heurística — segunda parte da #71, após #72

1. Acordar com a implementação da #72 um contrato de saída por `(repositorio, tag)` com predição binária `corretiva` e identificação da versão da heurística. Executar a heurística sobre as 300 releases sorteadas, sem expor as predições aos avaliadores antes de concluírem as planilhas.
2. Comparar as predições com o consenso de `corretiva`, verificando cobertura exata das chaves. Calcular precisão, recall e F1 para a classe positiva `sim` com `sklearn.metrics.precision_recall_fscore_support`; registrar suporte, matriz de confusão e regra para divisão por zero. Não apresentar a métrica como final se houver desempates pendentes ou releases sem predição.
3. Registrar no relatório a versão avaliada, os números e os erros mais relevantes. Se F1 < 0,70, devolver os falsos positivos/negativos à #72 para refino e repetir a avaliação; preservar os resultados de cada versão. O CFR (b) deve usar a versão final documentada.

### 4. Testes e aceite

- Adicionar `statsmodels` e `scikit-learn` com versões fixas a `requirements.txt`.
- Criar `tests/lab03/test_validacao_amostra_ouro.py` com fixtures pequenas para: alinhamento por chave apesar da ordem diferente; planilha faltante/incompleta; duplicata; kappa em cada dimensão; maioria; empate 1–1–1 sem decisão e com decisão; precisão/recall/F1, inclusive ausência de positivos e predição faltante.
- Atualizar `labs/lab03_dora/README.md` com comando reexecutável, arquivos produzidos e protocolo de desempate. Rodar a suíte `tests/lab03` e conferir os gates de cobertura do CI (Lab03 e `metricas/` >= 80%).
- Aceite final: três planilhas independentes completas e commitadas; três kappas interpretados; consenso rastreável sem pendências; precisão, recall e F1 da heurística final contra as 300 releases; versão e F1 documentados.

## Dependências e divisão de trabalho

| Ordem | Responsável sugerido | Entrega | Dependência |
| --- | --- | --- | --- |
| 1 | João | Rotulagem `rotulagem_joao.xlsx` (#69) | Amostra já sorteada (#67) |
| 1, em paralelo | Salomão | Rotulagem `rotulagem_salomao.xlsx` (#70); corrigir responsável da issue | Amostra já sorteada (#67) |
| 2 | João, com os três avaliadores nos desempates | Kappas, consenso, protocolo e testes (#71) | Três planilhas completas |
| 3, em paralelo à etapa 2 | Responsável da #72 | Heurística com predições versionadas e CFR (b) | Dados de releases |
| 4 | João | Métricas da heurística e relatório final da #71 | Consenso final e predições da #72 |
