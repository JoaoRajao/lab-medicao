# Lab04 — Roteiro da apresentação oral (15 perguntas)

Gerado por `python -m labs.lab04_ci.roteiro` a partir dos mesmos dados do dashboard (amostra real, resultados de Q1–Q3 e valores exatos da binomial). Não edite à mão: rode o comando de novo.

- Dashboard: <https://joaorajao-lab-medicao-labslab04-ciapp-jw2ure.streamlit.app/>
- Duração: até 7 minutos, cerca de 25 segundos por resposta. Cada resposta indica a seção do dashboard para mostrar enquanto fala.
- Resultados: Q1/Q2 simulados em `labs/lab04_ci/data/simulacao/resultados.csv`; **Q3 pendente (#100)**.

## Divisão

| Integrante | Perguntas |
| --- | --- |
| João | 1, 3, 4, 14, 15 |
| Pedro | 2, 5, 6, 7, 8 |
| Salomão | 9, 10, 11, 12, 13 |

## Respostas

### 1. Qual é o cenário de vocês e o que H₀ e H₁ afirmam, em palavras simples?

**João** · mostrar: 1. Cenário

Queremos saber se o CI do `astral-sh/ruff` falha mais do que a meta de 5%. H₀ diz que a chance de uma execução falhar é no máximo 5%; H₁ diz que é maior que 5%. Coletamos 30 execuções reais e comparamos dois testes que respondem essa mesma pergunta: o Z para uma proporção e o binomial exato.

### 2. O teste de vocês é unicaudal ou bicaudal? Por quê?

**Pedro** · mostrar: 1. Cenário

Unicaudal à direita. A meta só é descumprida se a taxa de falha for **maior** que 5%; uma taxa menor é boa notícia, não um problema. Por isso H₁ é p > 0,05 e só contagens altas de falhas contam como evidência contra H₀ — a região de rejeição fica toda na cauda direita.

### 3. Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição?

**João** · mostrar: 2. Os dados (G1)

Pela API do GitHub, pegamos as 30 execuções mais recentes do workflow `CI` disparadas por push em main, uma por commit, de 2026-10-30 a 2026-11-02; cada linha do CSV tem o link da execução. Deram 5 falhas e 25 sucessos (16,7%). Cada observação é 0 ou 1: a distribuição é fortemente assimétrica, concentrada em zero, sem outliers numéricos.

### 4. Como os dados reais ajudaram a escolher os parâmetros da simulação?

**João** · mostrar: 2. Os dados (G1)

O tamanho de cada conjunto simulado é o mesmo da amostra real, n = 30. Como o dado é binário, o modelo natural é Bernoulli independente; sob H₀ usamos p = 5%, a meta. Para o poder, a grade de taxas vai de 5% a 30% e cobre a taxa observada, 16,7%, que mostra o tamanho de efeito realista para o Ruff.

### 5. O que cada um dos dois testes compara de fato (médias, postos, proporções...)?

**Pedro** · mostrar: 3. Como os testes funcionam (G2)

Os dois olham para a **proporção de falhas**, ou seja, para o número de falhas X em n execuções. O Z padroniza essa proporção, (X − n·p₀)/√(n·p₀(1−p₀)), e compara com uma normal padrão — é uma aproximação. O binomial compara X diretamente com a distribuição Binomial(n; 0,05), que é a distribuição exata sob H₀.

### 6. No G2: o que é a distribuição da estatística sob H₀, e por que a região de rejeição fica onde fica?

**Pedro** · mostrar: 3. Como os testes funcionam (G2)

É o que a estatística faria se H₀ fosse verdadeira e repetíssemos a coleta muitas vezes: a normal padrão no Z e a Binomial(30; 0,05) no binomial. A região de rejeição fica na cauda direita porque H₁ é p > 5%; ela vai até onde a probabilidade sob H₀ soma 5%: z > 1,64, ou seja, 4 falhas ou mais, no Z, e 5 falhas ou mais no binomial.

### 7. O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa?

**Pedro** · mostrar: 3. Como os testes funcionam (G2)

Com 5 falhas, o p-valor é a chance de ver 5 ou mais falhas em 30 execuções **se a taxa verdadeira fosse 5%**: 0,0156 pelo binomial e 0,0017 pelo Z (z = 2,93). Ele **não** é a probabilidade de H₀ ser verdadeira, nem a chance de o resultado ser acaso, nem mede o tamanho do problema.

### 8. No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual dos dois seria mais grave?

**Pedro** · mostrar: 4. Erro tipo I (G3)

Erro tipo I: concluir que o CI passou da meta quando na verdade não passou — o time para para investigar uma instabilidade que não existe. Erro tipo II: não perceber que a taxa passou de 5% — as falhas continuam travando merges e tirando a confiança no CI. Para nós o tipo II é mais grave, porque o custo dele se acumula a cada execução, enquanto um alarme falso custa uma investigação.

### 9. No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê?

**Salomão** · mostrar: 4. Erro tipo I (G3)

Sim. Pela simulação com 10.000 repetições, o Z deu 6,0% e o binomial 1,7% em Base (n = 30). O Z ficou **liberal** e o binomial **conservador**. Como X é inteiro, os cortes saltam: o Z rejeita a partir de 4 falhas, o que sob H₀ tem probabilidade 6,1%, porque a normal subestima a cauda direita com n·p₀ = 1,5; o binomial só pode cortar em 5, que fica abaixo de 5% (1,6%).

### 10. No G4, qual teste tem mais poder? A diferença entre eles muda conforme o tamanho do efeito?

**Salomão** · mostrar: 5. Poder (G4)

O Z tem mais poder em todos os efeitos: com +10,0 p.p., o ponto da grade mais perto do efeito do Ruff (+11,7 p.p.), rejeita em 68,1% contra 48,0% do binomial. A diferença chega a 20,0 pontos em +10,0 p.p. e cai para 2,1 em +25,0 p.p., quando os dois rejeitam quase sempre. O poder extra do Z vem do mesmo corte mais baixo que o faz errar mais sob H₀ — não é vantagem gratuita.

### 11. Que violação de pressuposto vocês simularam, e por que ela afeta mais um teste do que o outro?

**Salomão** · mostrar: 4 e 5 (G3 e G4, situação adversa)

Pendente: a situação adversa é definida e simulada na #100; esta resposta é gerada quando os resultados existirem.

### 12. Se vocês usassem α = 0,01 em vez de 0,05, o que mudaria no G3 e no G4?

**Salomão** · mostrar: 4 e 5 (G3 e G4)

Os cortes sobem: com α = 0,01, o Z passa a rejeitar a partir de 5 falhas e o binomial a partir de 6. No G3 a linha de referência desce para 1% e o erro tipo I cai para 1,6% (Z) e 0,3% (binomial). No G4 as curvas descem: com a taxa do Ruff, o poder seria 57,6% (Z) e 38,4% (binomial). Menos alarmes falsos, mais erros tipo II.

### 13. A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença?

**Salomão** · mostrar: 1. Cenário → 4 e 5

Em parte. Esperávamos que o binomial controlasse melhor o erro tipo I, e isso se confirmou: 1,7% contra 6,0% do Z, que passou de 5%. Também esperávamos que o Z parecesse mais poderoso, e ele foi, mas a simulação mostrou que essa vantagem é justamente o preço do erro tipo I acima do nominal.

### 14. Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática?

**João** · mostrar: 6. Dados reais

Sim: os dois rejeitam H₀ com α = 0,05 — p = 0,0017 no Z e 0,0156 no binomial. O efeito é a taxa observada menos a meta, +11,7 pontos percentuais (h de Cohen = 0,39, efeito pequeno a médio). Na prática importa: 16,7% é cerca de uma falha a cada 6 execuções, 3,3 vezes a meta.

### 15. Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal limitação do estudo?

**João** · mostrar: 7. Conclusão

Recomendamos o **binomial exato**: ele nunca passa do α declarado, inclusive com amostras pequenas, e chegou à mesma conclusão nos dados reais. Mudaríamos para o Z com amostras grandes, em que n·p₀ passa de uns 10 e a normal aproxima bem — aí os dois quase coincidem e o Z é mais simples. A principal limitação: 30 execuções de poucos dias de um único projeto, e falhas de CI costumam vir em sequência, o que viola a independência que os dois testes assumem.
