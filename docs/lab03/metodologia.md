# Metodologia de Mineração e Validação das Métricas DORA

**Instituição:** Pontifícia Universidade Católica de Minas Gerais (PUC Minas) - Curso de Engenharia de Software  
**Disciplina:** Laboratório de Experimentação de Software  
**Repositório:** [https://github.com/JoaoRajao/lab-medicao](https://github.com/JoaoRajao/lab-medicao)  
**Quadro de Gestão (Kanban):** [https://github.com/users/JoaoRajao/projects/4](https://github.com/users/JoaoRajao/projects/4)  
**Autores:** João Vitor Pedersoli Rajao, Pedro Moreira Ramos, Otávio Salomão Ferreira  

---

## 1. Fonte de Dados e Janela Temporal

A coleta empírica baseia-se na extração automatizada de dados da API REST e GraphQL pública do GitHub. A janela temporal de observação abrange exatamente 12 meses: de **01/10/2025 a 30/09/2026**.

Para mitigar variações transientes de infraestrutura e garantir reprodutibilidade estrita sob cotas de requisição da API (*rate limits*), todas as chamadas HTTP são intermediadas por um cliente com cache persistente em disco (`ResponseCache`) e política exponencial de retentativas.

Os dados coletados compreendem:
- Metadados cadastrais do repositório (estrelas, tópicos, linguagem principal, contagem de contribuidores e URL).
- Histórico completo de releases e tags publicadas na janela temporal.
- Registros de execuções de fluxos de CI/CD via GitHub Actions (`/actions/runs`).
- Metadados dos commits associados a cada tag/release via Git API (`commit.author.date`, mensagens de commit e comparações de diff).

---

## 2. Funil de Seleção e Amostragem

A identificação dos projetos open-source utilizou a busca particionada por faixas de estrelas (`GET /search/repositories?q=stars:A..B`), ordenada decrescentemente das maiores contagens de estrelas até que a meta de 300 repositórios elegíveis fosse atingida (`labs/lab03_dora/data/selection_funnel.csv`).

O funil de refinamento aplicou sucessivamente os seguintes filtros objetivos:

| Etapa do Funil | Repositórios Restantes | Descartados | Motivo do Descarte |
|---|---:|---:|---|
| **1. Candidatos examinados** | 713 | — | Repositórios com `stars:>1000` avaliados ordenados por popularidade (40.865 a 552.497 estrelas). |
| **2. Adoção de GitHub Actions** | 643 | 70 | Ausência de workflows declarados (`total_count = 0` no endpoint `/actions/workflows`). |
| **3. Cadência mínima de releases** | 346 | 297 | Menos de 5 releases publicadas na janela temporal (`draft = false`, excluindo pré-releases). |
| **4. Atividade mínima em CI/CD** | 300 | 46 | Menos de 50 execuções válidas de workflow de CI (`push` na branch principal com status `success` ou `failure`). |
| **5. Amostra Final Consolidada** | **300** | 0 | Todos os 300 repositórios acessíveis e com metadados completos. |

A amostra final abrange repositórios amplamente consolidados no ecossistema global de software livre, com destaque para ecossistemas TypeScript (80), Python (71), Go (32), Rust (31) e JavaScript (29).

---

## 3. Definições Operacionais das Métricas DORA

Em virtude da ausência de eventos nativos padronizados de "implantação em produção" na plataforma GitHub, as quatro métricas DORA foram operacionalizadas através de aproximações empíricas (*proxies*):

### 3.1 Deployment Frequency (DF)
Mede a cadência de entregas ao usuário final. É quantificada pelo número de releases oficiais publicadas no período normalizado pela quantidade de semanas ativas da janela de observação.

$$\text{DF} = \frac{\text{Total de Releases Publicadas}}{\text{Semanas na Janela}}$$

A categorização segue os patamares DORA adaptados:
- **Elite:** $\ge 7$ por semana ($\ge 1$ ao dia).
- **High:** $\ge 1$ por semana e $< 7$ por semana.
- **Medium:** $\ge 1$ por mês e $< 1$ por semana.
- **Low:** $< 1$ por mês.

### 3.2 Lead Time for Changes (LTC)
Calcula a latência temporal entre a concepção do código e sua disponibilização em release:
- **Variante (a) — por Release:** Diferença temporal entre a data da release ($T_{\text{rel}}$) e o commit mais antigo ($T_{\text{commit\_min}}$) incorporado exclusivamente naquela release:
  $$\text{LTC}_{\text{rel}} = T_{\text{rel}} - \min_{c \in \text{Release}} (T_c)$$
- **Variante (b) — por Commit:** Diferença temporal calculada individualmente para cada commit contido na release frente à sua data de autoria (`commit.author.date`), extraindo-se a mediana agregada por repositório.

### 3.3 Change Failure Rate (CFR)
Avalia a proporção de entregas defeituosas através de duas abordagens complementares:
- **Variante (a) — CI Workflows:** Razão entre execuções de CI finalizadas com erro (`failure`, `timed_out`, `startup_failure`) e o total de execuções válidas concluídas na branch default (`success` + falhas):
  $$\text{CFR}_{\text{CI}} = \frac{N_{\text{falhas}}}{N_{\text{sucesso}} + N_{\text{falhas}}}$$
- **Variante (b) — Releases Corretivas (Heurística SemVer + Temporal):** Classifica uma release como corretiva (`corrective = sim`) caso ela atenda cumulativamente:
  1. Incremento de versão *Patch* sob especificação SemVer (`vX.Y.Z` onde $Z > 0$).
  2. Publicação em até 7 dias corridos após a release precedente.
  3. Presença de termos chave corretivos (*fix*, *bug*, *patch*, *hotfix*, *resolve*) nas notas de release ou mensagens de commit.

### 3.4 Failed Deployment Recovery Time (MTTR / Recovery Time)
Mensura o tempo decorrido desde o término de uma execução de workflow que falhou até a conclusão da primeira execução subsequente bem-sucedida no mesmo repositório e branch principal.

---

## 4. Protocolo de Validação Manual (Amostra-Ouro)

Para assegurar o rigor científico da heurística automatizada da Variante (b) do CFR e caracterizar a natureza dos projetos, foi executado um protocolo de amostragem e rotulagem cega com validação por múltiplos avaliadores:

1. **Sorteio Estratificado e Reprodutível:** A partir da semente pseudoaleatória `SEED = 42`, foram sorteados 60 repositórios da amostra final e 5 releases de cada repositório (totalizando 300 releases).
2. **Avaliação Independente por 3 Avaliadores:** Os três autores (Pedro, João e Salomão) preencheram de forma isolada e independente planilhas estruturadas (`rotulagem_pedro.xlsx`, `rotulagem_joao.xlsx`, `rotulagem_salomao.xlsx`), sem acesso aos rótulos dos pares nem ao resultado da heurística automatizada.
3. **Dimensões Avaliadas:**
   - *Aba Repositórios (60 itens):* `tipo_projeto` (`aplicacao/servico`, `biblioteca/framework`, `ferramenta CLI`, `outro`) e `entregas_reais` (`sim`, `nao`, `incerto`).
   - *Aba Releases (300 itens):* `corretiva` (`sim`, `nao`).
4. **Cálculo de Concordância Inter-Avaliadores (Kappa de Fleiss):**
   A concordância foi mensurada através do coeficiente $\kappa$ de Fleiss com interpretação pelas faixas de Landis & Koch:
   - `tipo_projeto`: $\kappa \approx 0{,}396$ (*concordância razoável*).
   - `entregas_reais`: $\kappa \approx -0{,}011$ (*abaixo do acaso*, decorrente da extrema homogeneidade da amostra, onde praticamente $100\%$ dos repositórios realizam entregas reais, provocando o clássico paradoxo de prevalência de Kappa).
   - `corretiva`: $\kappa \approx 0{,}088$ a $0{,}179$ (*concordância leve*), refletindo a discrepância intrínseca entre critérios estritos de hotfix versus inclusão mista de pequenos ajustes e features.
5. **Formação de Consenso e Avaliação da Heurística:**
   - O consenso final foi derivado por maioria simples ($2$ de $3$ votos), sem necessidade de desempate manual pendente (`pending_ties = 0`).
   - Confrontando o consenso da amostra-ouro com a heurística `semver-patch-v1` de `cfr_b_releases.csv`, obteve-se:
     - **Precisão:** $91{,}30\%$ (quando a heurística sinaliza corretiva, o acerto é de mais de $9$ em cada $10$).
     - **Recall:** $52{,}94\%$ (comportamento conservador da heurística, não capturando releases corretivas que não seguiram rigorosamente a janela de 7 dias ou SemVer patch estrito).
     - **F1-Score:** $0{,}6702$ ($67{,}02\%$), situando-se próximo à meta teórica de $0{,}70$.
