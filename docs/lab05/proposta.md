# Lab05 — Proposta (Lab05S01)

**Software estudado: SQLite**, o motor de banco de dados SQL embutido em celulares, navegadores, sistemas operacionais e linguagens de programação.

**Caminho:** rodar o software no ambiente do grupo (seção 2b do enunciado). Vamos fazer um experimento controlado com configurações de produção do SQLite: modo de journal `WAL` × `DELETE` e/ou `synchronous` `FULL` × `NORMAL`, sob a mesma carga.

| Seção | Issue | Situação |
| --- | --- | --- |
| 1. Software e evidências dos três critérios | #117 | Feita |
| 2. Pergunta de pesquisa, GQM, hipóteses e 7 categorias | #118 | Pendente |
| 3. Plano de coleta, instrumentação e coleta piloto | #119 | Pendente |

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

_A cargo de quem pegar a #118: caminho escolhido, objetivo no template GQM, métricas com escala, hipóteses, variáveis, 7 categorias da pesquisa com justificativa e plano de análise._

## 3. Plano de coleta, instrumentação e coleta piloto (#119)

_A cargo de quem pegar a #119: ambiente (hardware, sistema operacional, versão do SQLite e do Python), carga de trabalho, número de repetições, script de coleta versionado e dados do piloto._
