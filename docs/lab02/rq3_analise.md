# Lab02 - Analise RQ3

Base analisada: 12 trials consolidados (P1, P2). Os demais trials ainda nao entram nesta versao.
Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.

## Medianas e IQR

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Complexidade ciclomática media | manual | 6 | 6 | 3.75 | 6 | 2.25 | 2 | 9 | 5.33 |
| Complexidade ciclomática media | ai_assisted | 6 | 5 | 3.25 | 6.75 | 3.50 | 2 | 11 | 5.50 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Maintainability Index | manual | 6 | 59.27 | 57.05 | 64.28 | 7.24 | 56.45 | 72.27 | 61.59 |
| Maintainability Index | ai_assisted | 6 | 58.88 | 57.03 | 61.41 | 4.38 | 55.91 | 75.29 | 61.27 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LOC | manual | 6 | 25.50 | 17.25 | 30.75 | 13.50 | 16 | 35 | 24.83 |
| LOC | ai_assisted | 6 | 26.50 | 23 | 29.25 | 6.25 | 19 | 32 | 26 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Duplicacao (%) | manual | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Duplicacao (%) | ai_assisted | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Outliers

- Complexidade ciclomática media / manual: nenhum.
- Complexidade ciclomática media / ai_assisted: nenhum.
- Maintainability Index / manual: nenhum.
- Maintainability Index / ai_assisted: P2-support_queue-ai_assisted=75.29.
- LOC / manual: nenhum.
- LOC / ai_assisted: nenhum.
- Duplicacao (%) / manual: nenhum.
- Duplicacao (%) / ai_assisted: nenhum.

## Wilcoxon

| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |
| --- | ---: | ---: | ---: | ---: | --- |
| Complexidade ciclomática media | 2 | 0.17 | 1 | 1 | exact two-sided p-value |
| Maintainability Index | 2 | -0.32 | 1 | 1 | exact two-sided p-value |
| LOC | 2 | 1.17 | 1 | 1 | exact two-sided p-value |
| Duplicacao (%) | 2 | 0 | 0 | 1 | all differences are zero |

Com alfa=0.05, nenhuma hipotese nula foi rejeitada para as metricas estruturais.

## Discussao

- Complexidade: as medianas por tratamento ficam proximas, com variacao maior dependente do kata do que do tratamento.
- Maintainability Index: o `ai_assisted` fica ligeiramente abaixo na mediana, mas a diferenca e pequena para sustentar conclusao forte com esta amostra.
- LOC: o tratamento `ai_assisted` apresenta mediana maior, embora a diferenca pareada por participante seja pequena na amostra.
- Duplicacao: todos os registros tiveram duplicacao 0%, entao Wilcoxon e nao informativo nessa metrica.
- Interpretacao: RQ3 nao mostra evidencia robusta de degradacao estrutural causada por IA; o sinal mais claro e que solucoes variam mais pelo kata e estilo individual do que pelo tratamento.
