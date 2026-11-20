# Lab05 — Ameaças à validade (#123)

> **Revisão da S02, depois da coleta completa (#121).** As mitigações que dependem do script de coleta e da coleta foram conferidas. As que dependem dos testes estatísticos ficam marcadas para a análise (#122), que deve trazer os números observados (poder, p-valores, atípicos).

Coluna **Situação**:
- **Aplicada**: a mitigação está no script de coleta ou na coleta completa e foi conferida (código, teste automatizado ou dados versionados).
- **Planejada (#122 / #125)**: entra na análise ou no impacto.
- **Residual**: não há como mitigar no escopo do lab; vira limitação declarada.

## 1. Validade de conclusão

A relação entre configuração e desempenho é estatisticamente confiável?

| Ameaça | Risco no nosso estudo | Mitigação | Situação |
| --- | --- | --- | --- |
| Baixo poder estatístico | Com poucas repetições, um efeito real (ex.: leitura 1–2% mais lenta no WAL) pode passar despercebido. | 30 blocos. Antes da coleta completa, simular o erro tipo I e o poder do teste escolhido com a variabilidade do piloto, como no Lab04. | Planejada |
| Pressupostos do teste violados | As vazões são assimétricas e têm valores atípicos; um teste t poderia errar o p-valor. | Wilcoxon pareado por bloco (não paramétrico); teste t pareado só como análise de sensibilidade. | Planejada |
| Múltiplas comparações | Três hipóteses testadas com α = 0,05 inflam a chance de algum falso positivo. | Correção de Holm. | Planejada |
| Confiabilidade das medidas | Ruído do sistema operacional e resolução do relógio afetam medições muito curtas (uma leitura por chave primária leva poucos microssegundos). | `time.perf_counter()` (resolução abaixo de 1 µs); centenas ou milhares de operações por medição; coeficiente de variação reportado por configuração. | Aplicada na coleta (`perf_counter`, 500 escritas e 5.000 leituras por medição); coeficiente de variação na #122 |
| *Fishing* (procurar o resultado) | Escolher a métrica ou o teste depois de ver os dados. | Hipóteses, métricas e testes registrados na proposta (#118, S01), antes da coleta completa. Qualquer análise extra é apresentada como exploratória. | Aplicada |
| Significância sem relevância | Com muitas operações, diferenças pequenas ficam significativas. | Tamanho do efeito (razão das medianas, com intervalo de confiança, e correlação rank-bisserial) ao lado do p-valor. | Planejada |

## 2. Validade interna

A diferença observada é causada pela configuração, e não por outro fator?

| Ameaça | Risco no nosso estudo | Mitigação | Situação |
| --- | --- | --- | --- |
| Efeito de ordem e aquecimento | Cache do sistema de arquivos, temperatura e *turbo* da CPU mudam ao longo da coleta e favoreceriam quem roda antes ou depois. | Blocos completos com ordem sorteada (semente fixa); análise pareada por bloco. | Aplicada (ordem sorteada em cada bloco, conferida em `tests/lab05/test_dados.py`) |
| Estado residual entre medições | Um banco reaproveitado carregaria arquivos `-wal` e `-journal` e páginas em cache da medição anterior. | Banco novo a cada medição; `-wal`, `-shm` e `-journal` apagados ao final. | Aplicada |
| Atividade em segundo plano | Antivírus, indexação e atualizações do Windows disputam o disco e podem gerar valores atípicos isolados. A primeira execução da coleta completa rodou enquanto outros processos usavam a máquina. | Essa execução foi **descartada e repetida do zero** com a máquina ociosa, na tomada e sem outros programas abertos (registrado em `labs/lab05_sqlite/data/README.md`). Regra de atípicos fixada **antes da análise**: medição além de 3 × IQR dos quartis, por carga e configuração, é reportada e investigada, mas mantida no teste principal (o Wilcoxon é robusto a ela). | Aplicada na coleta; contagem de atípicos na #122 |
| Instrumentação | O SQLite ignora `PRAGMA` com valor inválido sem avisar; uma medição poderia rodar com a configuração errada. | O script deve recusar valores fora do experimento e conferir o valor efetivo (`PRAGMA journal_mode` / `PRAGMA synchronous`) antes de medir, com teste automatizado. | Aplicada |
| Diferenças entre máquinas | Se cada integrante coletar na própria máquina, a máquina se confunde com o tratamento. | A coleta completa foi feita em uma única máquina, então máquina e tratamento não se confundem. Se for repetida em outras máquinas, cada máquina entra como bloco, nunca como tratamento. | Aplicada |

## 3. Validade de construto

As métricas representam o que queremos dizer com "desempenho" e "durabilidade"?

| Ameaça | Risco no nosso estudo | Mitigação | Situação |
| --- | --- | --- | --- |
| Viés de operação única | Uma carga só (inserções de 200 bytes, 1 por transação) não representa "escrita" em geral. | Três cargas (escrita, leitura avulsa e leitura em uma transação); latência mediana e p95, além da vazão. O escopo (transações pequenas, um processo) fica declarado no texto. | Aplicada |
| Leitura em *autocommit* | Se cada consulta for uma transação própria, a medida inclui o custo de travar e destravar o arquivo, que é diferente no DELETE e no WAL. O resultado pode contrariar os "1–2% mais lento" que a documentação atribui ao WAL em leitura. | O piloto confirmou a divergência (WAL cerca de 6,6× mais rápido em leitura avulsa). A coleta completa já mede a variante com as consultas dentro de uma única transação (carga `leitura_transacao`), para separar os dois custos. | Aplicada na coleta; comparação na #122 |
| Durabilidade sem medição direta | M6 vem da documentação oficial, não de um teste de queda de energia. Seria uma medida de método único. | Declarar como medida documental. Opcional: encerrar o processo à força no meio das gravações e contar transações perdidas, sabendo que isso não equivale a uma queda de energia. | Residual |
| Métrica "jogável" (Goodhart) | Otimizar só transações por segundo levaria a recomendar `synchronous = OFF` e perder dados. | Durabilidade como contramétrica obrigatória; nenhuma recomendação de desempenho sem o custo em durabilidade. | Planejada (#118) |
| Expectativa dos pesquisadores | As hipóteses vêm da documentação do fornecedor, e o grupo poderia interpretar os dados a favor delas. | Análise automatizada por script a partir do CSV versionado; resultados contrários à documentação também são reportados. | Aplicada na coleta (CSV versionado, sem edição manual); análise por script na #122 |

## 4. Validade externa

Os resultados valem para outros ambientes e para quem usa o SQLite em produção?

| Ameaça | Risco no nosso estudo | Mitigação | Situação |
| --- | --- | --- | --- |
| Uma máquina e um sistema | Windows 11 com um SSD específico. A sincronização com o disco (`fsync`/`FlushFileBuffers`) varia muito entre discos e sistemas, e o valor absoluto de WAL + NORMAL depende disso. | Hardware e disco registrados em `coleta_completa_ambiente.json` (SSD NVMe Samsung MZVL4512HBLU). Generalizar só os efeitos **relativos**. Repetir nas máquinas dos outros integrantes continua possível e entraria como bloco. | Residual |
| Carga sintética | Apps reais misturam leituras e escritas concorrentes, transações maiores e índices secundários. | Declarar o escopo (transações pequenas, um processo); não extrapolar para concorrência alta nem para cargas analíticas. | Residual |
| Versão | Medimos a 3.50.4 (a do Python), enquanto a linha atual é a 3.54. | A linha 3.50 ainda recebe correções (3.50.8, em 13/11/2026). Opcional: repetir com a versão mais recente para ver se a conclusão se mantém. | Residual |
| *Driver* Python | O módulo `sqlite3` acrescenta um custo por chamada que um app em C, Kotlin ou Swift não teria. | O custo é igual em todas as configurações e não muda a comparação; o valor absoluto é apresentado como "via Python". | Residual |
| Extrapolação do impacto | Multiplicar o ganho por "bilhões de dispositivos" supõe que todos usam a mesma configuração e a mesma carga. | Na seção de impacto (#125), mostrar a conta como ordem de grandeza, com as fontes, e dizer explicitamente o que não pode ser afirmado. | Planejada (#125) |

## Pendências

- [x] Conferir se o script da #119 atende aos itens que eram **Requisito #119** e registra o hardware (incluindo o modelo do disco).
- [x] Definir antes da análise a regra para valores atípicos (3 × IQR, reportar e manter no teste principal).
- [x] Atualizar as situações com o que a coleta completa (#121) resolveu.
- [ ] Na análise (#122): preencher com os números observados (poder simulado, p-valores com Holm, atípicos encontrados, comparação entre as duas cargas de leitura).
- [ ] Ligar cada ameaça residual ao nível de evidência das 7 categorias (#126).
