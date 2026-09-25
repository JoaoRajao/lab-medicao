# Lab02 - Analise RQ3

Base analisada: 18 trials consolidados (P1, P2, P3). Os demais trials ainda nao entram nesta versao.
Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.

## Medianas e IQR

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Complexidade ciclomática media | manual | 9 | 6 | 3 | 6 | 3 | 2 | 9 | 4.89 |
| Complexidade ciclomática media | ai_assisted | 9 | 6 | 3 | 7 | 4 | 2 | 11 | 6 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Maintainability Index | manual | 9 | 60.72 | 57.83 | 65.47 | 7.64 | 56.45 | 73.18 | 62.62 |
| Maintainability Index | ai_assisted | 9 | 57.28 | 56.77 | 59.96 | 3.19 | 55.91 | 75.29 | 59.73 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LOC | manual | 9 | 21 | 19 | 30 | 11 | 16 | 35 | 23.78 |
| LOC | ai_assisted | 9 | 27 | 26 | 30 | 4 | 19 | 32 | 27.22 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Duplicacao (%) | manual | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Duplicacao (%) | ai_assisted | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Outliers

- Complexidade ciclomática media / manual: nenhum.
- Complexidade ciclomática media / ai_assisted: nenhum.
- Maintainability Index / manual: nenhum.
- Maintainability Index / ai_assisted: P2-support_queue-ai_assisted=75.29.
- LOC / manual: nenhum.
- LOC / ai_assisted: P1-sensor_anomaly-ai_assisted=19.
- Duplicacao (%) / manual: nenhum.
- Duplicacao (%) / ai_assisted: nenhum.

## Wilcoxon

| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |
| --- | ---: | ---: | ---: | ---: | --- |
| Complexidade ciclomática media | 3 | 3 | 2 | 0.7500 | exact two-sided p-value |
| Maintainability Index | 3 | -4.29 | 1 | 0.5000 | exact two-sided p-value |
| LOC | 3 | 2.67 | 1 | 0.5000 | exact two-sided p-value |
| Duplicacao (%) | 3 | 0 | 0 | 1 | all differences are zero |

Com alfa=0.05, nenhuma hipotese nula foi rejeitada para as metricas estruturais.

## Discussao

- Complexidade: as medianas por tratamento ficam proximas, com variacao maior dependente do kata do que do tratamento.
- Maintainability Index: o `ai_assisted` fica ligeiramente abaixo na mediana, mas a diferenca e pequena para sustentar conclusao forte com esta amostra.
- LOC: o tratamento `ai_assisted` apresenta mediana maior, embora a diferenca pareada por participante seja pequena na amostra.
- Duplicacao: todos os registros tiveram duplicacao 0%, entao Wilcoxon e nao informativo nessa metrica.
- Interpretacao: RQ3 nao mostra evidencia robusta de degradacao estrutural causada por IA; o sinal mais claro e que solucoes variam mais pelo kata e estilo individual do que pelo tratamento.
