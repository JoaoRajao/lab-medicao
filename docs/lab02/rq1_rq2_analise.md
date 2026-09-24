# Lab02 - Analise RQ1/RQ2

Base analisada: 12 trials consolidados (P1, P2). Os demais trials ainda nao entram nesta versao.
Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.

## RQ1 - Tempo ate verde

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tempo ate verde (s) | manual | 6 | 780 | 422.25 | 1193.25 | 771 | 380 | 1622 | 866 |
| Tempo ate verde (s) | ai_assisted | 6 | 31 | 20.25 | 45.50 | 25.25 | 14 | 51 | 32.33 |

### Outliers de tempo

- Tempo ate verde (s) / manual: nenhum.
- Tempo ate verde (s) / ai_assisted: nenhum.

## RQ2 - Sucesso e falhas

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Taxa de sucesso | manual | 6 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| Taxa de sucesso | ai_assisted | 6 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |

| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Falhas nos testes | manual | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Falhas nos testes | ai_assisted | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Outliers de sucesso/falhas

- Taxa de sucesso / manual: nenhum.
- Taxa de sucesso / ai_assisted: nenhum.
- Falhas nos testes / manual: nenhum.
- Falhas nos testes / ai_assisted: nenhum.

## Wilcoxon

| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |
| --- | ---: | ---: | ---: | ---: | --- |
| Tempo ate verde (s) | 2 | -833.67 | 0 | 0.5000 | exact two-sided p-value |
| Taxa de sucesso | 2 | 0 | 0 | 1 | all differences are zero |
| Falhas nos testes | 2 | 0 | 0 | 1 | all differences are zero |

Com alfa=0.05, nenhuma hipotese nula foi rejeitada: tempo, sucesso e falhas tiveram p-valor acima do limiar ou diferencas pareadas todas iguais a zero.

## Discussao

- Tempo: o tratamento `ai_assisted` apresenta mediana menor que `manual`. A diferenca aparece nos dois participantes consolidados, com os tempos manuais de P2 atualizados a partir do cronometro externo informado.
- Sucesso: todos os trials terminaram verdes, entao a taxa de sucesso e 1.0 para ambos os tratamentos.
- Falhas: todos os registros finais tem `tests_failed = 0`; por isso, Wilcoxon para sucesso/falhas e nao informativo e retorna diferencas zero.
- Interpretacao: com n pequeno e katas curtos, os resultados devem ser lidos como evidencia exploratoria. A mediana/IQR e mais apropriada que media simples porque reduz impacto de tempos extremos.
