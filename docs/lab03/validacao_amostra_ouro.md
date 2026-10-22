# Validação da amostra-ouro

## Proveniência da rotulagem

A amostra sorteada contém 60 repositórios e 300 releases. Pedro e Salomão rotularam
manualmente; João completou 420 rótulos com assistência de IA.

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

## Resultados

| Dimensão | Kappa de Fleiss | Interpretação (Landis e Koch) |
| --- | ---: | --- |
| Tipo do projeto | 0,396 | razoável |
| Entregas reais | -0,011 | abaixo do acaso (paradoxo da prevalência: quase todos "sim") |
| Release corretiva | 0,088 | leve |

O consenso marca 238 das 300 releases como corretivas (79%); Pedro marcou 49%, Salomão 82% e João 85%.
Não houve empates 1-1-1.

## Avaliação e refino da heurística

`python -m labs.lab03_dora.avaliar_heuristicas` recalcula todas as versões testadas
(`amostra_ouro/heuristicas_f1.csv`):

| Versão | Precisão | Recall | F1 (consenso) | F1 (só Pedro) |
| --- | ---: | ---: | ---: | ---: |
| `semver-patch-v1` (só patch) | 0,913 | 0,529 | 0,670 | 0,566 |
| patch ou qualquer commit fix | 0,836 | 0,941 | 0,885 | 0,697 |
| patch ou ≥ 50% dos commits fix | 0,913 | 0,618 | 0,737 | 0,660 |
| **`semver-patch-commits-fix-v2`** (patch ou ≥ 1/3) | **0,909** | **0,752** | **0,823** | **0,719** |
| referência: tudo corretiva | 0,793 | 1,000 | 0,885 | 0,661 |

A v1 ficou abaixo da meta de 0,70. O sinal de texto dela nunca era aplicado, porque `releases.csv` não
tinha as mensagens dos commits; a coleta passou a registrar, por release, quantos commits desde a anterior
são correções (`fix_commits`). Com 79% de positivos no consenso, "marcar tudo" já atinge F1 0,885, então
um F1 alto contra esse consenso não basta. A v2 foi escolhida por passar de 0,70 contra o consenso e contra
o único avaliador sem assistência de IA, com precisão de 0,91, marcando 66% das releases em vez de quase
todas. O relatório oficial (`validacao_relatorio.json`) usa a v2: F1 0,823.
