# Plano de implementação — João, Sprint 2 do Lab03

Base: `feature/sprint2`, criada a partir de `origin/master` em 14/10/2026 (`5709437`).
Escopo de João: [#69](https://github.com/JoaoRajao/lab-medicao/issues/69),
[#71](https://github.com/JoaoRajao/lab-medicao/issues/71) e
[#72](https://github.com/JoaoRajao/lab-medicao/issues/72).

## Estado e dependências

- A amostra-ouro já contém 60 repositórios e 300 releases (5 por repositório). `rotulagem_pedro.xlsx` está completa; `rotulagem_joao.xlsx` e `rotulagem_salomao.xlsx` estão sem rótulos. O leitor `amostra_ouro.read_labels()` exige rótulos válidos em todas as linhas.
- #70 é a rotulagem independente do terceiro avaliador. Ela fica fora do escopo de João, mas a #71 precisa dessa planilha completa. No GitHub, #70 está sem responsável e #72 está atribuída a João.
- A versão inicial da heurística (`semver-patch-v1`) e o CFR (b) já foram implementados e executados sobre os CSVs coletados. A validação F1 ainda depende do consenso.
- O módulo de kappa e consenso está implementado, mas a execução final fica bloqueada pelas planilhas incompletas de João e Salomão.

## 1. #69 — rotulagem independente de João

1. Usar `rotulagem_joao.xlsx` como registro final. Classificar `tipo_projeto` e `entregas_reais` nos 60 repositórios e `corretiva` nas 300 releases, sem consultar as planilhas dos outros avaliadores nem a saída da heurística.
2. `labs/lab03_dora/sugestoes_rotulagem.py` já gerou `labs/lab03_dora/amostra_ouro/sugestoes_automaticas_joao.csv` com 420 sugestões e colunas vazias para decisão final, revisor e data. O método é `regras-codex-v1`: regras escritas pelo assistente, não uma inferência de modelo de linguagem por item. O arquivo não leu outras planilhas nem predições da #72 e não alterou `rotulagem_joao.xlsx`.
3. A página `labs/lab03_dora/amostra_ouro/revisao_joao.html` já mostra evidências e sugestões para cada item, grava as escolhas no navegador e exporta `revisao_joao.csv`. Depois da revisão, conferir o CSV, preservar a sugestão e a origem por item e incorporar apenas os rótulos finais válidos a `rotulagem_joao.xlsx`. O registro por item deve usar `automatico_revisado` para decisões que partiram de sugestão; a planilha preserva o formato esperado por `read_labels()`.
4. Rodar `amostra_ouro.read_labels()` e verificar 60/300 linhas, chaves únicas, valores válidos e correspondência com os CSVs sorteados. Não executar `amostra_ouro.py --forcar`, que apagaria os rótulos. Commitar a planilha apenas após a revisão.

**Registro no relatório:** em `docs/lab03/validacao_amostra_ouro.md`, criar a seção `Proveniência da rotulagem` com método, versão das regras, quantidade de rótulos humanos, revisados e não revisados, protocolo de revisão e limitações. O `labs/lab03_dora/README.md` aponta para essa seção. Assim, a origem fica registrada por item no CSV e resumida na metodologia do estudo.

**Limite metodológico:** preenchimento inteiramente automático pode ser registrado como rotulagem por IA, mas não deve ser apresentado como julgamento independente de João. Para dispensar a revisão humana, o grupo precisa alterar e aprovar explicitamente o protocolo da amostra-ouro e os critérios de aceite da #69; nesse caso, usar um arquivo `rotulagem_ia.xlsx` separado e declarar na #71 e no relatório que o consenso inclui um avaliador automático. Não usar a heurística da #72 como rotulador, pois a validação ficaria circular.

## 2. #72 — heurística de release corretiva e CFR (b)

1. A função pura em `labs/lab03_dora/metricas/cfr_b.py` já classifica releases por incremento de patch SemVer; aceita palavras como `fix`, `hotfix` e `revert` se houver texto. O `releases.csv` completo não contém notas/commits, portanto a execução atual usa apenas as tags. A classificação por release registra regra, evidência e versão.
2. Criar a etapa de coleta/cálculo em `labs/lab03_dora/` e registrá-la em `pipeline.py`. Ordenar releases publicadas por repositório; para cada release R, verificar se a próxima release corretiva ocorreu em até 7 dias. Excluir do denominador as releases publicadas nos últimos 7 dias da janela e reportar a censura. Definir comportamento para múltiplas releases no intervalo e limites exatos de 7 dias.
3. Gerar `cfr_b_metrics.csv` com `repository`, `cfr_b`, `releases_evaluated` e `releases_censored`, compatível com `consolidacao.py`, além de um CSV auditável por release com classificação, evidência, falha atribuída e censura. Regerar `dataset.csv` a partir do novo arquivo.
4. Testar o exemplo da issue (`v2.3.0` seguida de `v2.3.1` com `fix:`; `v2.4.0` seguida de `v2.5.0`) e bordas: janela, limite de 7 dias, falta de release posterior, tag não SemVer e evidência ausente. Documentar cada versão testada. A versão final só é escolhida após a avaliação da #71; se F1 < 0,70, refinar e repetir.

## 3. #71 — concordância, consenso e avaliação

1. Criar `labs/lab03_dora/validacao_amostra_ouro.py` para ler as três planilhas com `read_labels()`, associar repositórios por `repositorio` e releases por `(repositorio, tag)`, rejeitar duplicatas, chaves faltantes e rótulos incompletos. A ordem das linhas não deve mudar o resultado.
2. Calcular kappa de Fleiss separadamente para `tipo_projeto`, `entregas_reais` e `corretiva`, usando `statsmodels.stats.inter_rater.aggregate_raters` e `fleiss_kappa`. Registrar n, categorias, distribuição, valor e interpretação de Landis & Koch, inclusive valores negativos.
3. Formar consenso por maioria simples. Casos 1–1–1 ficam pendentes até decisão registrada pelos três avaliadores; preservar rótulos individuais e justificativa do desempate. Produzir CSVs de consenso e divergências em `amostra_ouro/` e documentar o protocolo em `docs/lab03/validacao_amostra_ouro.md`.
4. Comparar a predição versionada da #72 com o consenso de `corretiva`, exigindo cobertura exata das 300 releases. Calcular precisão, recall e F1 para `sim` com `sklearn.metrics.precision_recall_fscore_support`; registrar suporte, matriz de confusão, erros e regra para divisão por zero. Guardar o F1 de cada versão da heurística e selecionar a versão final para o CFR (b).

## Verificação e aceite

- Fixar versões de `statsmodels` e `scikit-learn` em `requirements.txt`.
- Adicionar testes com fixtures em `tests/lab03/` para a rotulagem assistida sem vazamento de dados, alinhamento por chave, planilhas incompletas, kappa, maioria, empate, precisão/recall/F1 e todos os casos de CFR (b). Atualizar `labs/lab03_dora/README.md` com os comandos reexecutáveis.
- Rodar `tests/lab03` e conferir os gates de cobertura do CI (Lab03 e `metricas/` >= 80%).
- Aceite: planilha de João completa e auditável (#69); heurística versionada e CFR (b) por repositório (#72); três kappas, consenso sem pendências e avaliação da versão final da heurística (#71). A #71 aguarda a planilha do terceiro avaliador (#70), mesmo fora deste escopo.
