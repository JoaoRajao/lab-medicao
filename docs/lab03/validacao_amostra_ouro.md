# Validação da amostra-ouro — estado da Sprint 2

## Proveniência da rotulagem

A amostra sorteada contém 60 repositórios e 300 releases. Pedro entregou sua planilha
independente; as planilhas de João e Salomão ainda não têm rótulos finais. Nenhum kappa,
consenso ou F1 foi reportado antes das três entregas.

O arquivo `labs/lab03_dora/amostra_ouro/sugestoes_automaticas_joao.csv` contém 420
sugestões preliminares, produzidas por `regras-codex-v1`. Esse método consiste em regras
de texto propostas pelo assistente e executadas localmente, sem consultar rótulos de Pedro
ou Salomão nem a saída da heurística da #72. As colunas `rotulo_final`, `revisor` e
`revisado_em` permanecem vazias. As sugestões não compõem a amostra-ouro e não são
tratadas como rótulos humanos.

Quando João revisar cada item na página `labs/lab03_dora/amostra_ouro/revisao_joao.html`,
exportar `revisao_joao.csv`, preservar a sugestão original e preencher
`rotulagem_joao.xlsx` com os rótulos finais. A origem então será
"automática revisada por João", mesmo que o rótulo final coincida com a sugestão.
Rótulos inteiramente automáticos não podem ser apresentados como julgamento de João.

## Protocolo de concordância

`labs/lab03_dora/validacao_amostra_ouro.py` alinha as três planilhas por repositório ou
por (repositório, tag), rejeita chaves duplicadas/ausentes e calcula o kappa de Fleiss
separadamente para tipo de projeto, entregas reais e corretividade. A interpretação usa
as faixas de Landis e Koch. O consenso usa maioria simples; casos 1–1–1 exigem
decisão dos avaliadores em `desempates.csv`, com justificativa, antes de publicar o
consenso final.

Depois disso, o módulo confronta o consenso de corretividade com
`data/cfr_b_releases.csv` e calcula precisão, recall e F1 para a classe positiva
`sim`. O F1 de `semver-patch-v1` ainda não é conhecido e a meta de 0,70 não pode ser
verificada neste estado.
