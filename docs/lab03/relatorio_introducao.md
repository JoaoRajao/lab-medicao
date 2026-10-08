# Laboratório 03 - Mineração de Métricas DORA em Repositórios Open-Source
## Relatório Parcial: Introdução e Hipóteses de Pesquisa (Sprint 1)

**Instituição:** Pontifícia Universidade Católica de Minas Gerais (PUC Minas) - Curso de Engenharia de Software  
**Disciplina:** Laboratório de Experimentação de Software (Prof. Danilo Maia)  
**Repositório:** [https://github.com/JoaoRajao/lab-medicao](https://github.com/JoaoRajao/lab-medicao)  
**Quadro de Gestão (Kanban):** [https://github.com/users/JoaoRajao/projects](https://github.com/users/JoaoRajao/projects)  
**Autores:**
- João Vitor Pedersoli Rajao (`joaorajao5@gmail.com`)
- Pedro Moreira Ramos (`pedromoreiraramos1998@gmail.com`)
- Otávio Salomão Ferreira (`otavio.ferreira.mds@gmail.com`)

---

## 1. Contexto e Relevância das Métricas DORA

As métricas DORA (*DevOps Research and Assessment*) tornaram-se o padrão de mercado para avaliar o desempenho e a maturidade dos processos de entrega de software, dividindo-se entre velocidade (*throughput*) e estabilidade:

| Métrica | O que mede (Definição DORA) | Dimensão |
|---|---|---|
| **Deployment Frequency (DF)** | Com que frequência a equipe coloca mudanças em produção | Velocidade |
| **Lead Time for Changes (LTC)** | Tempo desde a submissão de um commit até a publicação em produção | Velocidade |
| **Change Failure Rate (CFR)** | Proporção de deploys que exigem intervenção/correção | Estabilidade |
| **Failed Deployment Recovery Time (MTTR)** | Tempo para se recuperar de uma falha de deploy | Estabilidade |
| **Deployment Rework Rate (Bônus RQ08)** | Proporção de deploys não planejados feitos para refazer/corrigir alterações | Estabilidade |

### 1.1 O Desafio da Operacionalização em Repositórios Open-Source

Diferente de ambientes corporativos fechados, o GitHub não registra "deploys em produção" nem "falhas em produção" por padrão. Por isso, a mineração depende de **aproximações operacionais** (*proxies*):
- **Deploys:** Releases/Tags publicadas ou execuções bem-sucedidas de workflows de CI/CD.
- **Lead Time:** Diferença de tempo entre o commit/PR e a publicação da release (por release) ou incorporação no branch principal (por commit).
- **Falhas de Deploy:** Taxa de workflows de CI com falha (`failure`/`cancelled`) ou lançamentos de releases corretivas (*patch/hotfix*).
- **Recuperação:** Intervalo entre a falha do workflow de CI e a próxima execução bem-sucedida.

---

## 2. Questões de Pesquisa e Hipóteses Informais

Formuladas formalmente **antes** da finalização da coleta e análise de dados:

### RQ 01 — Frequência de Deploys
- **Questão:** Qual é a frequência de deploy típica de repositórios open-source populares?
- **Hipótese Informal (H01):** Espera-se frequência nas categorias **"Medium"** (1 por mês a 1 por semana) ou **"High"** (uma por semana a algumas por dia), e raramente **"Elite"** (diária).
- **Justificativa:** Desenvolvimento assíncrono e voluntário em projetos open-source reduz a cadência diária de entregas em produção quando comparado a equipes SaaS corporativas.

### RQ 02 — Lead Time para Mudanças
- **Questão:** Qual é o lead time para mudanças em repositórios open-source populares?
- **Hipótese Informal (H02):** Espera-se lead time mediano em **"High"** ou **"Medium"** (1 dia a 30 dias), com discrepância marcante entre a variante por release (lead time maior) e a variante por commit/PR (lead time menor).
- **Justificativa:** Commits integrados ao branch principal costumam aguardar o fechamento do ciclo de release formal antes da publicação da versão.

### RQ 03 — Taxa de Falha em Mudanças (Change Failure Rate - CFR)
- **Questão:** Qual é a taxa de falha de deploy/mudança em repositórios open-source populares?
- **Hipótese Informal (H03):** Para a variante (a) (CI workflows), espera-se taxa moderada a alta ($\ge 30\%$). Para a variante (b) (releases corretivas), espera-se taxa baixa (**"Elite"** ou **"High"**, $\le 15\%$).
- **Justificativa:** CI atua como barreira estrita para barrar PRs quebrados, acumulando mais falhas registradas do que o histórico final de releases publicadas.

### RQ 04 — Tempo de Recuperação de Falhas (Recovery Time)
- **Questão:** Quanto tempo leva para um repositório open-source se recuperar de uma falha de deploy/integração?
- **Hipótese Informal (H04):** Espera-se tempo mediano na faixa **"High"** a **"Medium"** (de horas a poucos dias).
- **Justificativa:** Ausência de escalas de plantão 24/7 em projetos voluntários faz com que correções dependam da disponibilidade dos mantenedores.

### RQ 05 — Correlação entre Frequência e Taxa de Falhas
- **Questão:** Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falhas?
- **Hipótese Informal (H05):** Não se espera correlação positiva forte entre frequência e falhas ($r \le 0$).
- **Justificativa:** Em alinhamento com a literatura DORA, entregas mais frequentes amparadas por CI/CD automatizado não sacrificam a estabilidade do produto.

### RQ 06 — Relação entre Métricas DORA e Características do Repositório
- **Questão:** Como as métricas DORA se correlacionam com contribuidores, estrelas e tipo de projeto?
- **Hipótese Informal (H06):** Repositórios mais populares, com mais contribuidores e projetos do tipo aplicação/CLI terão maior frequência de deploy e menor lead time do que bibliotecas de base.
- **Justificativa:** Aplicações/CLIs possuem menor risco sistêmico de quebra de retrocompatibilidade para dependentes externos do que bibliotecas de infraestrutura.

### RQ 07 — Sensibilidade da Classificação DORA às Definições Operacionais
- **Questão:** O nível de desempenho DORA (Elite, High, Medium, Low) é sensível às aproximações operacionais adotadas?
- **Hipótese Informal (H07):** Espera-se alta sensibilidade e variações significativas de categoria (baixo a moderado Kappa de Cohen) ao alternar os *proxies* de deploy e falha.
- **Justificativa:** A falta de registros diretos de produção no GitHub faz com que cada proxy reflita facetas distintas do processo de desenvolvimento.

---

## 3. Metadados do Projeto

- **Arquivo LaTeX para Submissão:** `docs/lab03/introducao.tex`
- **Link do Repositório:** `https://github.com/JoaoRajao/lab-medicao`
- **Link do Quadro de Gestão:** `https://github.com/users/JoaoRajao/projects`
