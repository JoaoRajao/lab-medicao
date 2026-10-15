# Validação da amostra-ouro — estado da Sprint 2

## Proveniência da rotulagem

A amostra sorteada contém 60 repositórios e 300 releases. Pedro entregou sua planilha
independente; as planilhas de João e Salomão ainda não têm rótulos finais. Nenhum kappa,
consenso ou F1 foi reportado antes das três entregas.

João declarou ter registrado a rotulagem independentemente em papel. A transcrição para
`labs/lab03_dora/amostra_ouro/rotulagem_joao.csv` e `rotulagem_joao.xlsx` está
pendente do recebimento dessas anotações. O CSV deve conter 420 decisões identificadas
por repositório, tag e dimensão. Nenhum valor será inferido de outras planilhas ou da
heurística da #72.

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
