# Validação dos katas - Lab02S01

Complementa a issue #29 (Preparação dos katas e testes de aceitação): confirma que os testes de
aceitação sao de fato solucionaveis, mede objetivamente a dificuldade comparavel exigida pelo
enunciado, e verifica a baixa indexacao dos 6 katas.

## 1. Gabaritos (reference solutions)

Antes desta validacao, nenhum kata tinha uma implementacao correta conhecida -- so o stub
(`raise NotImplementedError`). Isso significa que os testes de aceitacao nunca tinham sido
executados contra uma solucao de verdade, e um teste com bug so seria descoberto durante um
trial real, gastando o time-box de 35 minutos de um participante.

Foi adicionado um `reference_solution.py` por kata (implementacao seguindo o `README.md` de cada
um), mais `scripts/verify_kata_references.py`, que troca temporariamente `solution.py` pelo
gabarito, roda os testes de aceitacao de verdade via pytest, e restaura o stub original -- sem
alterar o fluxo real de trial.

```bash
python -m labs.lab02_ia_vs_manual.scripts.verify_kata_references
```

### Resultado

| Kata | Resultado |
| --- | --- |
| dependency_unlock | PASS |
| invoice_window | PASS |
| route_reconciliation | PASS |
| sensor_anomaly | PASS (apos correcao, ver secao 4) |
| support_queue | PASS |
| warehouse_batches | PASS |

## 2. Dificuldade comparavel (medida via Radon)

O enunciado do Lab02 pede "katas/exercicios de programacao de dificuldade comparavel". Isso nunca
tinha sido medido objetivamente -- so afirmado. Rodando Radon nos gabaritos:

| Kata | Complexidade ciclomatica | LOC | SLOC | Indice de manutenibilidade |
| --- | ---: | ---: | ---: | ---: |
| dependency_unlock | C (11) | 30 | 22 | 55.91 |
| invoice_window | A (3) | 27 | 22 | 57.28 |
| route_reconciliation | B (7) | 32 | 26 | 56.77 |
| sensor_anomaly | B (6) | 19 | 15 | 59.96 |
| support_queue | A (2) | 19 | 14 | 73.18 |
| warehouse_batches | A (4) | 27 | 22 | 60.89 |

**Observacao:** LOC e indice de manutenibilidade ficam numa faixa razoavelmente proxima entre os
6 katas. A complexidade ciclomatica, porem, **nao e equivalente**: `dependency_unlock` (ordenacao
topologica com deteccao de ciclo e desempate alfabetico) mede C(11), bem acima dos demais
(A/B, 2-7). Isso e uma limitacao real a documentar no relatorio final -- `dependency_unlock` e
objetivamente mais complexo que, por exemplo, `support_queue` (A, 2). Nao foi trocado nem
re-escrito aqui porque redesenhar o conjunto de katas esta fora do escopo desta validacao (e
cabe a quem preparou os katas originalmente, issue #29); fica registrado como achado para o grupo
decidir se mantem, ajusta ou documenta como ameaca a validade adicional no Relatorio Final.

## 3. Baixa indexacao (busca por indicios de memorizacao)

Buscas na web pelo nome e pela descricao de cada kata, procurando por exercicios indexados com o
mesmo enunciado (risco: um assistente de IA reproduzir uma solucao ja vista no treinamento em vez
de efetivamente ajudar):

| Kata | Busca | Resultado |
| --- | --- | --- |
| dependency_unlock | ordenacao topologica com desbloqueio de tarefas | Padrao algoritmico (topological sort) e bem conhecido em geral, mas nenhum exercicio indexado com este enunciado/nome especifico foi encontrado |
| route_reconciliation | comparacao de rotas planejadas vs executadas | Nenhum exercicio indexado encontrado |
| warehouse_batches | consolidacao de lotes por SKU/validade | Nenhum exercicio indexado com este enunciado encontrado (ha problemas de LeetCode sobre "warehouse", mas de logica totalmente diferente -- empacotamento geometrico) |
| invoice_window | calculo de fatura com desconto/multa | Nenhum exercicio indexado encontrado (so material generico de contas a receber) |
| sensor_anomaly | deteccao de anomalia por faixa/salto | Nenhum exercicio indexado com este enunciado encontrado |
| support_queue | priorizacao de fila de suporte por SLA/severidade | Nenhum exercicio indexado com este enunciado encontrado |

Nenhum dos 6 katas apareceu como exercicio indexado com o mesmo enunciado. O unico ponto de
atencao e que `dependency_unlock` usa um padrao algoritmico classico (ordenacao topologica) que um
assistente de IA pode reconhecer e resolver de forma generica -- diferente de "decorar a solucao
exata", mas ainda vale mencionar como nuance no Relatorio Final.

## 4. Bug encontrado e corrigido: `sensor_anomaly`

O teste `test_first_reading_is_checked_only_by_range` esperava que, para as leituras
`[120.0, 118.0, 117.0]` com faixa valida `[0, 100]`, so o indice 0 fosse sinalizado como anomalia.
Pela regra do proprio `README.md` do kata ("Uma leitura e anomala se `value` ficar fora do
intervalo `[min_value, max_value]`", sem excecao), os indices 1 e 2 (118.0 e 117.0) tambem estao
fora da faixa e deveriam ser sinalizados. O teste tinha a expectativa incompleta.

Rodar o gabarito contra o teste original falhava (`1 failed, 1 passed`), confirmando o problema
antes de qualquer trial real acontecer. O teste foi corrigido para esperar as 3 anomalias de
`range`, mantendo o proposito original (a leitura 0 e sinalizada so por faixa, nunca por "jump",
por nao ter antecessora).

## Conclusao

Com os gabaritos, os 6 katas tem ao menos uma solucao correta confirmada contra os testes de
aceitacao reais -- inclusive o bug encontrado em `sensor_anomaly`, corrigido antes do inicio da
Lab02S02. A dificuldade comparavel se sustenta para LOC/indice de manutenibilidade, mas nao
totalmente para complexidade ciclomatica (`dependency_unlock` e um outlier) -- registrado aqui
para o grupo decidir o encaminhamento e para constar no Relatorio Final como limitacao conhecida.
