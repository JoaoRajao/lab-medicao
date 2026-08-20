# Validação e Hipóteses - RQ01 e RQ02

Este documento descreve o processo de validação de consistência dos dados e a análise das hipóteses informais referentes às duas primeiras questões de pesquisa (RQs) do laboratório, com base no conjunto de dados final dos 1.000 repositórios mais populares do GitHub por quantidade de estrelas.

---

## RQ01 - Sistemas populares são maduros/antigos?

Métrica: Idade do repositório em dias (`age_days`), calculada a partir da data de criação (`created_at`) até a data de coleta.

### Estatísticas Gerais de Idade

| Estatística | Valor (dias) | Valor (anos aprox.) |
| --- | ---: | ---: |
| Mínimo | 0 | 0.0 anos |
| Média | 2.792,27 | 7,65 anos |
| Mediana | 2.819,00 | 7,72 anos |
| Q1 (25%) | 1.287,50 | 3,53 anos |
| Q3 (75%) | 4.146,75 | 11,36 anos |
| P90 | 4.959,20 | 13,58 anos |
| P95 | 5.419,00 | 14,84 anos |
| P99 | 6.016,06 | 16,48 anos |
| Máximo | 6.698 | 18,35 anos |

### Distribuição por Faixas de Idade

| Faixa | Repositórios | Percentual |
| --- | ---: | ---: |
| Menos de 1 ano (< 365 dias) | 81 | 8,1% |
| 1 a 3 anos (365 - 1.095 dias) | 113 | 11,3% |
| 3 a 5 anos (1.095 - 1.825 dias) | 128 | 12,8% |
| 5 a 10 anos (1.825 - 3.650 dias) | 334 | 33,4% |
| Mais de 10 anos (> 3.650 dias) | 344 | 34,4% |

### Outliers e Consistência
- Aplicando a regra do IQR (Interquartile Range) para identificação de outliers:
  - \(IQR = 4.146,75 - 1.287,50 = 2.859,25\)
  - Limite inferior: \(1.287,50 - 1,5 \times 2.859,25 = -3.001,37\) (dias negativos)
  - Limite superior: \(4.146,75 + 1,5 \times 2.859,25 = 8.435,62\) dias
- Não foram encontrados outliers estatísticos de idade na amostra. Os repositórios mais antigos (máximo de 6.698 dias, cerca de 18,3 anos) estão bem abaixo do limite de corte superior do IQR.
- Todos os repositórios possuem idade maior ou igual a zero, e a data de criação é anterior à data de coleta.

### Hipótese Informal
A hipótese inicial de que os sistemas populares são antigos e maduros é **fortemente confirmada**. Apenas 8,1% dos repositórios populares têm menos de 1 ano de idade. A grande maioria (67,8%) tem mais de 5 anos de existência, e a mediana de idade é de 7,7 anos, sugerindo que a popularidade expressiva de um projeto no GitHub (medida por estrelas) exige tempo significativo para consolidação e atração de comunidade.

---

## RQ02 - Sistemas populares recebem muita contribuição externa?

Métrica: Número de Pull Requests aceitos (`accepted_pull_requests`), definido como a contagem de PRs no estado `MERGED`.

### Estatísticas Gerais de PRs Aceitos

| Estatística | Valor (PRs) |
| --- | ---: |
| Mínimo | 0 |
| Média | 4.317,65 |
| Mediana | 798,00 |
| Q1 (25%) | 178,75 |
| Q3 (75%) | 3.403,50 |
| P90 | 10.072,10 |
| P95 | 19.890,95 |
| P99 | 62.546,31 |
| Máximo | 103.013 |

### Distribuição por Faixas de PRs Aceitos

| Faixa | Repositórios | Percentual |
| --- | ---: | ---: |
| Sem PRs aceitos (0) | 18 | 1,8% |
| Poucos PRs (1 - 99) | 161 | 16,1% |
| Moderado (100 - 499) | 233 | 23,3% |
| Alto (500 - 1.999) | 260 | 26,0% |
| Muito alto (>= 2.000) | 328 | 32,8% |

### Outliers e Consistência
- Aplicando a regra do IQR:
  - \(IQR = 3.403,50 - 178,75 = 3.224,75\)
  - Limite superior de corte: \(3.403,50 + 1,5 \times 3.224,75 = 8.240,62\) PRs
- Foram identificados **126 repositórios outliers** com volumes de PRs aceitos acima de 8.240. Isso indica uma distribuição de cauda longa altamente assimétrica, onde uma minoria de projetos super-populares concentra a maior parte da atividade colaborativa da plataforma.
- **Top 10 Outliers em PRs Aceitos:**
  1. `firstcontributions/first-contributions` (103.013 PRs)
  2. `llvm/llvm-project` (96.378 PRs)
  3. `elastic/elasticsearch` (95.265 PRs)
  4. `getsentry/sentry` (91.019 PRs)
  5. `home-assistant/core` (89.918 PRs)
  6. `cockroachdb/cockroach` (75.714 PRs)
  7. `rust-lang/rust` (73.425 PRs)
  8. `grafana/grafana` (69.208 PRs)
  9. `ClickHouse/ClickHouse` (68.688 PRs)
  10. `kubernetes/kubernetes` (65.646 PRs)

### Hipótese Informal
A hipótese inicial de que sistemas populares recebem muita contribuição externa é **confirmada**. A mediana da amostra é alta (798 PRs aceitos) e 58,8% dos projetos possuem mais de 500 PRs aceitos/merged. Embora haja um pequeno grupo de repositórios que não recebem contribuições substanciais via PR (1,8% com zero e 16,1% com menos de 100), o padrão geral para a grande maioria é de forte colaboração externa.
