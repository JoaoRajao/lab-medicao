# Lab05 — Proposta (Lab05S01)

**Software estudado: SQLite**, o motor de banco de dados SQL embutido em celulares, navegadores, sistemas operacionais e linguagens de programação.

**Caminho:** rodar o software no ambiente do grupo (seção 2b do enunciado). Vamos fazer um experimento controlado com configurações de produção do SQLite: modo de journal `WAL` × `DELETE` e/ou `synchronous` `FULL` × `NORMAL`, sob a mesma carga.

| Seção | Issue | Situação |
| --- | --- | --- |
| 1. Software e evidências dos três critérios | #117 | Feita |
| 2. Pergunta de pesquisa, GQM, hipóteses e 7 categorias | #118 | Feita |
| 3. Plano de coleta, instrumentação e coleta piloto | #119 | Feita (piloto rodado) |

---

## 1. Software e evidências dos três critérios (#117)

### 1.1 Candidatos e escolha

| Candidato | Caminho | Por que não / por que sim |
| --- | --- | --- |
| PostgreSQL 15 × 17 | Rodar no ambiente do grupo | É um dos exemplos do próprio enunciado, então é provável que outro grupo o escolha, e cada software só pode ser estudado por um grupo. Também exige servidor e um benchmark mais pesado. |
| Incidentes em páginas de status (ex.: Slack) | Analisar dados de operação | Reaproveita as métricas DORA do Lab03, mas a API pública devolve poucos incidentes. Para ter uma amostra útil seria preciso raspar o histórico a 1 requisição por segundo. |
| **SQLite** ✅ | Rodar no ambiente do grupo | Atende aos três critérios com folga (tabela abaixo) e roda localmente, sem sistema de terceiros, sem limite de requisições e sem dados pessoais. Já vem com o Python (`sqlite3`), o que permite automatizar a coleta e fazer o piloto na S01. O desenho com dois tratamentos casa com o que fizemos no Lab04 (teste de hipótese, erro tipo I, poder e dashboard). |

**O objeto de estudo é o software em funcionamento, não o repositório.** Não vamos minerar commits, issues ou pull requests nem analisar o código-fonte. O SQLite nem é desenvolvido no GitHub (usa o Fossil), então não há risco de cair na restrição da seção 2a.

### 1.2 Os três critérios

| Critério | Evidência | Fonte (acesso em 19/11/2026) |
| --- | --- | --- |
| **Real** | Software com site oficial, documentação completa e licença em domínio público. É distribuído como biblioteca embutida nas aplicações, não como servidor. | [sqlite.org](https://www.sqlite.org/) · [About SQLite](https://www.sqlite.org/about.html) |
| **Em operação** | Mantido ativamente: a linha 3.54 recebeu as versões 3.54.0 (09/10/2026) e 3.54.1 (16/10/2026). Em **13/11/2026** saíram correções para três linhas antigas ainda mantidas: 3.53.6, 3.50.8 e 3.44.7. A versão que vamos medir é a **3.50.4**, embutida no Python 3.14.7 do ambiente do grupo; a linha 3.50 continua recebendo correções. | [Release History / Chronology](https://www.sqlite.org/chronology.html) |
| **Em operação (quem usa em produção)** | O Google usa o SQLite no Android e no Chrome; a Apple, em muitos apps nativos do macOS e do iOS; a Microsoft, como componente central do Windows 10; a Mozilla, como formato principal de metadados do Firefox e do Thunderbird. A Airbus confirma o uso no software de voo do A350 XWB. Python (desde a versão 2.5) e PHP já vêm com o SQLite. | [Well-Known Users of SQLite](https://www.sqlite.org/famous.html) |
| **Alto impacto** | Segundo o site oficial, "há mais de 4,0 bilhões de smartphones em uso ativo, cada um com centenas de arquivos de banco SQLite"; por isso é "provável que existam mais de um trilhão (10¹²) de bancos SQLite em uso ativo". Ele está em todo dispositivo Android e iOS, todo Mac, toda instalação do Windows 10/11 e todo Firefox, Chrome e Safari, e é provavelmente a segunda biblioteca de software mais implantada do mundo, depois da zlib. | [Most Widely Deployed SQL Database Engine](https://www.sqlite.org/mostdeployed.html) |
| **Alto impacto (números de terceiros)** | O Google anunciou mais de **3 bilhões de dispositivos Android ativos** em maio de 2021, no Google I/O. A Apple informou mais de **2,5 bilhões de dispositivos ativos** em janeiro de 2026, nos resultados do 1º trimestre fiscal de 2026. Os dois números se referem a plataformas que trazem o SQLite. | [TechCrunch, 18/05/2021](https://techcrunch.com/2021/05/18/android-now-powers-3b-devices) · [MacRumors, 29/01/2026](https://www.macrumors.com/2026/01/29/apple-2-5-billion-active-devices/) |

**Cuidados com esses números (validade externa):**
- O "trilhão de bancos" é uma **extrapolação do próprio fornecedor**, não uma contagem; o site diz que "números precisos são difíceis de obter".
- As bases do Android e da Apple têm datas e métodos diferentes; a do Android conta só aparelhos com Google Play. Por isso não devem ser somadas como se fossem uma estimativa única.
- Na seção de impacto (#125), usaremos esses números como ordem de grandeza, com a conta explícita, deixando claro o que não é possível afirmar.

### 1.3 Por que o SQLite combina com a pergunta do estudo

O próprio fornecedor documenta um *trade-off* que dá para medir com um experimento controlado:

- O modo **WAL** "é significativamente mais rápido na maioria dos cenários" e deixa leitores e escritores trabalharem em paralelo. Para aplicações que só leem, porém, pode ser "muito levemente mais lento (talvez 1% ou 2%)".
- No WAL, `synchronous = NORMAL` deixa de sincronizar o disco a cada *commit*. Isso acelera as gravações, mas "as transações deixam de ser duráveis e podem ser desfeitas após uma queda de energia".

Fonte: [Write-Ahead Logging](https://www.sqlite.org/wal.html).

Como essas configurações são escolhidas por quem desenvolve apps, navegadores e sistemas, o resultado tem leitura direta para quem usa o SQLite. A pergunta, as hipóteses e as métricas ficam na #118.

### 1.4 Pendência

- [ ] **Confirmar com o professor que nenhum outro grupo escolheu o SQLite** (exigido pela seção 10 do enunciado).

---

## 2. Pergunta de pesquisa, GQM, hipóteses e 7 categorias (#118)

### 2.1 Pergunta de pesquisa e caminho

> **Quanto as configurações de journal (`WAL` × `DELETE`) e de sincronização (`FULL` × `NORMAL`) do SQLite mudam a vazão e a latência de escrita e de leitura, e o que se perde em durabilidade em troca?**

**Caminho:** rodar o software no ambiente do grupo (seção 2b). É um experimento controlado com o SQLite 3.50.4, a versão embutida no Python 3.14 e de uma linha que ainda recebe correções (seção 1.2). A documentação oficial (seção 1.3) serve para formular as hipóteses e para comparar os resultados com o que o fornecedor afirma.

### 2.2 GQM

**Objetivo (template de Basili):**

| Campo | Valor |
| --- | --- |
| Analisar | o SQLite 3.50 com diferentes configurações de `journal_mode` e `synchronous` |
| com o propósito de | avaliar |
| com respeito a | desempenho de escrita e de leitura (vazão e latência) e durabilidade |
| do ponto de vista de | quem desenvolve aplicações que embutem o SQLite (apps móveis, navegadores, desktop) |
| no contexto de | um computador do grupo (Windows 11, Python 3.14), com cargas sintéticas de transações pequenas |

**Perguntas e métricas:**

| Pergunta | Métricas |
| --- | --- |
| **Q1.** O WAL aumenta a vazão de escrita em relação ao DELETE? | M1 transações/s · M2 latência mediana por transação · M3 latência p95 |
| **Q2.** O WAL muda o desempenho de leitura? | M4 consultas/s · M5 latência mediana por consulta |
| **Q3.** Quanto o `synchronous = NORMAL` acelera as gravações, e o que custa em durabilidade? | M1 e M3 nos dois níveis · M6 durabilidade após queda de energia |
| **Q4.** Quão estável é cada configuração entre repetições? | M7 coeficiente de variação da vazão entre blocos |

### 2.3 Métricas: entidade, atributo e escala

| Métrica | Entidade | Atributo | Medida | Escala | Estatísticas permitidas |
| --- | --- | --- | --- | --- | --- |
| Duração da medição (s) | Produto (SQLite em execução) | Comportamento temporal: eficiência de desempenho, ISO/IEC 25010 (externo) | Direta | Razão | Todas, incluindo razões ("X vezes mais rápido") |
| M1/M4 operações por segundo | Produto | Capacidade de vazão (externo) | Derivada (operações ÷ duração) | Razão | Todas; mediana e razão de medianas |
| M2/M5 latência mediana, M3 p95 (ms) | Produto | Comportamento temporal (externo) | Derivada (percentis das latências individuais) | Razão | Todas |
| M6 durabilidade | Produto | Confiabilidade: tolerância a falhas (externo) | Direta, pela documentação oficial | Nominal (durável / não durável) | Moda e frequências; nada de médias |
| M7 coeficiente de variação | Produto | Estabilidade do desempenho | Derivada (desvio padrão ÷ média) | Razão | Todas |
| `journal_mode`, `synchronous` | Configuração (variável independente) | — | Direta | Nominal | Contagem por nível |

**Armadilhas de medição (Goodhart, Campbell e McNamara):**
- Se a meta fosse só "mais transações por segundo", a resposta trivial seria `synchronous = OFF`, que dispensa a sincronização com o disco e aceita perder dados. Por isso a durabilidade (M6) entra como contramétrica, e o desempenho nunca é recomendado sem ela.
- Microbenchmark não é aplicação real. O número absoluto depende do disco e do sistema operacional; o que se generaliza melhor é a comparação relativa entre configurações na mesma máquina.

### 2.4 Hipóteses e variáveis

As hipóteses são comparadas por bloco, com α = 0,05 e correção de Holm para as três hipóteses.

| Hipótese | H₀ | H₁ | Cauda |
| --- | --- | --- | --- |
| **H-1 Escrita × journal** (com `synchronous = FULL`, o padrão) | vazão de escrita do WAL ≤ DELETE | WAL > DELETE | Unicaudal: a documentação diz que o WAL é "significativamente mais rápido" |
| **H-2 Leitura × journal** | vazão de leitura do WAL = DELETE | WAL ≠ DELETE | Bicaudal: a documentação prevê o WAL 1–2% mais lento, e o piloto indicou o contrário (seção 3.4) |
| **H-3 Escrita × synchronous** (no WAL) | vazão com NORMAL ≤ FULL | NORMAL > FULL | Unicaudal |

- **Variáveis independentes (fatores):** `journal_mode` ∈ {DELETE, WAL} e `synchronous` ∈ {FULL, NORMAL}. São 4 tratamentos.
- **Variáveis dependentes:** M1 a M5 e M7.
- **Variáveis controladas:**
  - versão do SQLite e do Python, máquina, tamanho do registro (200 bytes) e tamanho de cada carga;
  - banco novo a cada medição;
  - mesma semente para a ordem dos tratamentos e para os dados.
- **Objetos:** arquivos de banco SQLite criados pelo script. Não há participantes humanos.
- **Desenho:** fatorial 2 × 2 em **blocos completos aleatorizados**. Cada bloco mede as 8 combinações (4 tratamentos × 2 cargas) em ordem sorteada, então variações da máquina ao longo do tempo afetam todas as combinações de forma parecida. Planejamos 30 blocos (seção 3.2).

### 2.5 Plano de análise

1. **Estatística descritiva** por configuração e carga:
   - mediana, IQR, mínimo, máximo e coeficiente de variação;
   - gráfico de caixa ou de pontos em **escala logarítmica**, porque as vazões variam em ordens de grandeza (seção 3.4).
2. **Testes:** **Wilcoxon pareado por bloco** para H-1 a H-3.
   - Pareado porque cada bloco mede todos os tratamentos.
   - Não paramétrico porque o piloto já mostrou valores atípicos e assimetria.
   - Usaremos o **teste t pareado** como sensibilidade, para ver se a conclusão muda.
3. **Tamanho do efeito:**
   - **razão das medianas** (por exemplo, "o WAL faz 3 vezes mais transações por segundo"), com intervalo de confiança de 95% por *bootstrap*;
   - **correlação rank-bisserial** do Wilcoxon.

   A escala de razão permite falar em "vezes mais rápido".
4. **Interação journal × synchronous:** gráfico de interação descritivo. Se o efeito do `synchronous` depender do modo de journal, a recomendação precisa ser por combinação.
5. **Reaproveitamento do Lab04:** antes da coleta completa, simular o erro tipo I e o poder do Wilcoxon pareado com n = 30, usando a variabilidade do piloto. Isso justifica o número de blocos, como fizemos com o Z × binomial.

### 2.6 As 7 categorias da pesquisa (primeira versão)

| Categoria | Classificação | Justificativa |
| --- | --- | --- |
| Natureza | **Aplicada** | Responde a uma decisão prática de configuração tomada por quem desenvolve apps, navegadores e sistemas, não a uma questão teórica. |
| Objetivos | **Explicativa** (com parte descritiva) | Busca a relação de causa e efeito entre configuração e desempenho, manipulando a configuração. A magnitude dos efeitos é descrita com estatística descritiva. |
| Abordagem | **Quantitativa** | Todas as métricas de desempenho são numéricas em escala de razão. A durabilidade é uma variável nominal tirada da documentação oficial. |
| Procedimentos | **Experimental**, com apoio de **pesquisa documental** | Manipulamos as variáveis independentes em ambiente controlado. A documentação oficial do SQLite fundamenta as hipóteses e os números de impacto. |
| Tempo | **Transversal** | As medições são feitas em uma janela curta, com uma única versão. Não acompanhamos a evolução entre versões. |
| Controle | **Experimento controlado em laboratório** | O grupo controla o ambiente e os fatores, sorteia a ordem dos tratamentos em blocos e repete 30 vezes. |
| Nível de evidência | **Alto para validade interna, limitado para validade externa** | O experimento controlado e aleatorizado sustenta a causalidade nesta máquina e nesta carga. A generalização para outros discos, sistemas e cargas reais é limitada: uma máquina e carga sintética (ameaças na #123). |

## 3. Plano de coleta, instrumentação e coleta piloto (#119)

### 3.1 Ambiente

Registrado automaticamente em `labs/lab05_sqlite/data/raw/<nome>_ambiente.json` a cada coleta.

| Item | Piloto |
| --- | --- |
| SQLite | 3.50.4 (o que vem com o Python) |
| Python | 3.14.7 |
| Sistema | Windows 11 (10.0.26200) |
| Processador | AMD64 Family 25 (Zen 3/4), 12 núcleos lógicos |
| Data | 19/11/2026 |

### 3.2 Procedimento

O script é [`labs/lab05_sqlite/coleta.py`](../../labs/lab05_sqlite/coleta.py):

```bash
python -m labs.lab05_sqlite.coleta --piloto          # S01: 5 blocos, cargas pequenas (~16 s)
python -m labs.lab05_sqlite.coleta --repeticoes 30   # S02: coleta completa (estimativa: poucos minutos)
```

1. **Configuração:**
   - Cada medição cria um banco novo em uma pasta temporária e aplica `PRAGMA journal_mode` e `PRAGMA synchronous`.
   - Em seguida **confere se a configuração foi aplicada**, porque o SQLite ignora valores inválidos sem avisar.
   - Ao final, apaga o banco e os arquivos `-wal`, `-shm` e `-journal`.
2. **Carga de escrita:** N transações, cada uma com `BEGIN`, 1 `INSERT` de 200 bytes e `COMMIT`. É o padrão de um app que grava a cada ação do usuário. Coleta completa: N = 500; piloto: 200.
3. **Carga de leitura:**
   - A tabela é populada fora da medição (20.000 linhas; piloto: 5.000).
   - São medidas K consultas `SELECT` por chave primária sorteada (K = 5.000; piloto: 2.000), cada uma em modo *autocommit*, como em um app que faz consultas avulsas.
4. **Blocos:** cada bloco mede as 8 combinações em ordem sorteada (semente 42). Coleta completa: 30 blocos; piloto: 5.
5. **Saída:** `labs/lab05_sqlite/data/raw/<nome>.csv`, com uma linha por medição. Colunas: bloco, ordem, carga, configuração, operações, duração, ops/s, latência mediana, p95, versão do SQLite e semente.

### 3.3 Ética

Tudo roda na máquina do grupo:
- nenhum sistema de terceiros é acessado, então não há teste de carga externo nem limite de requisições a respeitar;
- os dados gravados são **sintéticos** (texto aleatório);
- não há dados pessoais nem participantes.

### 3.4 Resultados do piloto e problemas encontrados

Dados em [`labs/lab05_sqlite/data/raw/piloto.csv`](../../labs/lab05_sqlite/data/raw/piloto.csv). Medianas de 5 blocos:

| Carga | journal | synchronous | Operações/s (mediana) | Latência mediana (ms) | p95 (ms) | Coef. de variação |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Escrita | DELETE | FULL | 150 | 6,64 | 7,67 | 0,04 |
| Escrita | DELETE | NORMAL | 214 | 4,44 | 5,03 | 0,05 |
| Escrita | WAL | FULL | 461 | 2,14 | 2,27 | 0,29 |
| Escrita | WAL | NORMAL | 72.396 | 0,010 | 0,027 | 0,04 |
| Leitura | DELETE | FULL | 53.244 | 0,018 | 0,021 | 0,07 |
| Leitura | DELETE | NORMAL | 53.210 | 0,018 | 0,021 | 0,06 |
| Leitura | WAL | FULL | 352.361 | 0,003 | 0,003 | 0,02 |
| Leitura | WAL | NORMAL | 369.399 | 0,003 | 0,003 | 0,03 |

Esses números são **só do piloto** (n = 5); não servem como conclusão.

**O que o piloto mostrou:**

1. **O script funciona e é rápido.** Os 5 blocos levaram cerca de 16 s; a coleta completa cabe em poucos minutos por máquina.
2. **As escritas seguem a documentação.** O WAL fez cerca de 3 vezes mais transações por segundo que o DELETE com `FULL`.
   - Com `WAL + NORMAL`, a vazão salta para cerca de 72 mil por segundo, porque deixa de haver sincronização com o disco a cada *commit*. É exatamente a troca por durabilidade que a documentação descreve (M6).
   - A ordem de grandeza depende muito do disco. **Pendência:** registrar o modelo do disco (SSD/NVMe) no arquivo de ambiente.
3. **As leituras contrariam a documentação.** O WAL foi cerca de 6,6 vezes mais rápido que o DELETE, enquanto a documentação fala em WAL "1–2% mais lento".
   - Hipótese: cada `SELECT` em *autocommit* abre a própria transação de leitura. No DELETE, isso exige travar e destravar o arquivo pelo sistema operacional (e procurar um journal pendente); no WAL, a leitura usa o índice em memória compartilhada (`-shm`).
   - Isso é uma questão de **validade de construto**: o resultado mede "consultas avulsas", não "leitura em geral".
   - **Decisão para a S02:** manter a carga em *autocommit*, que é realista para apps, e avaliar uma variante com as consultas dentro de uma única transação para separar os dois efeitos.
4. **Valor atípico.** No bloco 5, `escrita/WAL/FULL` caiu para 204 transações por segundo, com p95 de 12 ms (os outros blocos ficaram entre 457 e 508).
   - Causa provável: atividade de disco em segundo plano, como antivírus ou indexação do Windows.
   - **Mitigação:**
     - 30 blocos, com ordem sorteada;
     - estatísticas robustas (medianas e Wilcoxon);
     - máquina na tomada e sem outros programas abertos durante a coleta;
     - registro de qualquer evento atípico.
5. **Validação da instrumentação.** O SQLite aceita `PRAGMA synchronous = <valor inválido>` sem erro. O script recusa configurações fora do experimento e confere o valor efetivo antes de medir. Isso está coberto por `tests/lab05/test_coleta.py`.

### 3.5 Reaproveitado dos labs anteriores

- **Lab04:**
  - semente fixa e CSV versionado como contrato entre a coleta e a análise;
  - testes automatizados (`pytest`);
  - escolha do teste de hipótese pela escala e pelo desenho, e simulação de erro tipo I e poder para justificar o tamanho da amostra (seção 2.5).
- **Labs 01 a 04:** *Kanban* no GitHub Projects com snapshot por sprint.
