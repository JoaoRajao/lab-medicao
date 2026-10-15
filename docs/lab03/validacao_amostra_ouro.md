# Validação da amostra-ouro — estado da Sprint 2

## Proveniência da rotulagem

A amostra sorteada contém 60 repositórios e 300 releases. Pedro entregou sua planilha;
João completou 420 rótulos com assistência de IA; a planilha de Salomão ainda está
incompleta. Nenhum kappa, consenso ou F1 foi reportado antes das três entregas.

`labs/lab03_dora/amostra_ouro/rotulagem_joao.csv` registra cada rótulo final, a sugestão
original, a evidência automática e a proveniência `humano_assistido_ia`. João confirmou as
257 sugestões que já tinham rótulo válido e decidiu `sim` para as 163 sugestões de
corretividade que a IA havia marcado `incerto`. As mesmas decisões foram incorporadas à
planilha `rotulagem_joao.xlsx`. Portanto, os rótulos de João **não são independentes das
sugestões de IA**; qualquer análise de concordância deve explicitar essa limitação. Não
foram usados os rótulos de Pedro ou Salomão para preencher a planilha de João.

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
