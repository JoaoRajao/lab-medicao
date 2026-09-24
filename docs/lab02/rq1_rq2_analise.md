# Lab02 - Analise RQ1/RQ2

Base analisada: 18 trials consolidados (P1, P2, P3). Os demais trials ainda nao entram nesta versao.
Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.

## RQ1 - Tempo ate verde

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tempo ate verde (s) | manual | 9 | 510 | 393 | 1050 | 657 | 310 | 1622 | 757.33 |
| Tempo ate verde (s) | ai_assisted | 9 | 30 | 22 | 35 | 13 | 14 | 51 | 31 |

### Outliers de tempo

- Tempo ate verde (s) / manual: nenhum.
- Tempo ate verde (s) / ai_assisted: nenhum.

## RQ2 - Sucesso e falhas

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Taxa de sucesso | manual | 9 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| Taxa de sucesso | ai_assisted | 9 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Falhas nos testes | manual | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Falhas nos testes | ai_assisted | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Outliers de sucesso/falhas

- Taxa de sucesso / manual: nenhum.
- Taxa de sucesso / ai_assisted: nenhum.
- Falhas nos testes / manual: nenhum.
- Falhas nos testes / ai_assisted: nenhum.

## Wilcoxon

| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |
| --- | ---: | ---: | ---: | ---: | --- |
| Tempo ate verde (s) | 3 | -511.67 | 0 | 0.2500 | exact two-sided p-value |
| Taxa de sucesso | 3 | 0 | 0 | 1 | all differences are zero |
| Falhas nos testes | 3 | 0 | 0 | 1 | all differences are zero |

Com alfa=0.05, nenhuma hipotese nula foi rejeitada: tempo, sucesso e falhas tiveram p-valor acima do limiar ou diferencas pareadas todas iguais a zero.

## Discussao

- Tempo: o tratamento `ai_assisted` apresenta mediana menor que `manual`. A diferenca aparece nos dois participantes consolidados, com os tempos manuais de P2 atualizados a partir do cronometro externo informado.
- Sucesso: todos os trials terminaram verdes, entao a taxa de sucesso e 1.0 para ambos os tratamentos.
- Falhas: todos os registros finais tem `tests_failed = 0`; por isso, Wilcoxon para sucesso/falhas e nao informativo e retorna diferencas zero.
- Interpretacao: com n pequeno e katas curtos, os resultados devem ser lidos como evidencia exploratoria. A mediana/IQR e mais apropriada que media simples porque reduz impacto de tempos extremos.
