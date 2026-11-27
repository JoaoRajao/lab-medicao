# Lab05 — Robustez: replicação, durabilidade medida e concorrência (#137)

> Gerado por `python -m labs.lab05_sqlite.robustez` a partir de `coleta_*.csv`, `durabilidade.csv`, `concorrencia.csv` em `labs/lab05_sqlite/data/raw`.

## 1. Replicação em outros ambientes

A coleta completa (30 blocos × 3 cargas × 4 configurações, o mesmo script e a mesma semente) foi repetida em outros ambientes, e cada um foi analisado com os mesmos testes do estudo principal:

- **Notebook · Linux (WSL2):** Ubuntu 26.04 no mesmo notebook, bancos no ext4 (o `/tmp` do WSL fica em memória e foi evitado). Mudam o sistema, o sistema de arquivos e a versão do SQLite; o hardware é o mesmo.
- **Actions:** máquinas virtuais do GitHub Actions com Ubuntu, Windows e macOS (`.github/workflows/lab05-replicacao.yml`). Hardware diferente do nosso, mas compartilhado e com ruído: servem para conferir a direção, não a magnitude.

| Ambiente | SQLite |
| --- | --- |
| Notebook · Windows | 3.50.4 |
| Notebook · Linux (WSL2) | 3.46.1 |
| Actions · Ubuntu | 3.46.1 |
| Actions · Windows | 3.50.4 |
| Actions · macOS | 3.50.4 |

| Comparação | Notebook · Windows | Notebook · Linux (WSL2) | Actions · Ubuntu | Actions · Windows | Actions · macOS | Mesma direção | Mesma conclusão |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | :---: |
| **H-1** Escrita: WAL > DELETE (FULL) | 3,16× · p < 0,001 | 1,95× · p < 0,001 | 2,30× · p < 0,001 | 5,67× · p < 0,001 | 4,85× · p < 0,001 | 5/5 | 5/5 |
| **H-2** Leitura avulsa: WAL ≠ DELETE (FULL) | 5,31× · p < 0,001 | 2,18× · p < 0,001 | 2,00× · p < 0,001 | 2,91× · p < 0,001 | 2,17× · p < 0,001 | 5/5 | 5/5 |
| **H-3** Escrita: NORMAL > FULL (WAL) | 168× · p < 0,001 | 442× · p < 0,001 | 17,31× · p < 0,001 | 10,47× · p < 0,001 | 8,34× · p < 0,001 | 5/5 | 5/5 |
| **E-1** Leitura em 1 transação: WAL ≠ DELETE (FULL) | 0,99× · p 0,626 | 0,99× · p 0,309 | 0,99× · p 0,015 | 0,99× · p 0,028 | 1,00× · p 0,543 | 4/5 | 3/5 |
| **E-2** Escrita: NORMAL > FULL (DELETE) | 1,46× · p < 0,001 | 1,26× · p < 0,001 | 1,14× · p < 0,001 | 1,16× · p < 0,001 | 1,14× · p < 0,001 | 5/5 | 5/5 |

Razão das medianas; p de Holm nas confirmatórias (H) e p bruto nas exploratórias (E). Os intervalos de confiança estão em `data/processed/robustez_replicacao.csv`.

**Leitura:** a direção se repete em 24 de 25 pares (comparação × ambiente) e a conclusão do teste em 23 de 25. A **magnitude** varia bastante entre ambientes, porque o custo de sincronizar o disco e de travar arquivos depende do sistema e do hardware. Por isso o estudo afirma efeitos relativos (direção e ordem de grandeza) e não um número universal.

Em **E-1** o efeito é praticamente nulo em todos os ambientes (razões entre 0,986 e 1,001), então "mesma direção" não tem significado ali: o sinal de uma diferença de menos de 2% oscila com o ruído, e com 30 blocos uma diferença tão pequena às vezes fica significativa. A conclusão que se repete é a de E-1 ser desprezível perto de H-2.

## 2. Durabilidade medida (M6)

Um processo grava transações de 1 `INSERT` e, a cada `COMMIT` confirmado, avisa quem controla o teste e espera a resposta antes da próxima (como um app que grava a cada ação do usuário). Depois de 1 a 8 s sorteados, provocamos a falha e contamos quantas transações **já confirmadas** sumiram.

- **Falha de processo** (30 rodadas por configuração, Windows): o processo é encerrado à força, como um app que trava. O sistema operacional continua de pé.
- **Queda do sistema** (20 rodadas por configuração, Linux): reinício imediato com `echo b > /proc/sysrq-trigger`, sem gravar o cache nem desmontar o disco, o método usual para simular queda de energia. Antes, testamos que `wsl --terminate` e `wsl --shutdown` gravam o cache e não servem. Cada rodada confere que o Linux de fato reiniciou (o `boot_id` muda).
- **DELETE/EXTRA** entra só aqui: é a correção que a documentação indica para o modo DELETE, porque com FULL o SQLite não sincroniza a pasta depois de apagar o journal, e esse apagamento é o que confirma a transação.

| Falha | Configuração | Rodadas com perda (IC 95%) | Transações perdidas por rodada (mediana · máx.) | Banco íntegro |
| --- | --- | ---: | ---: | ---: |
| Processo | `DELETE/FULL` | 0 de 30 (0%; 0%–12%) | 0 · 0 | 30 de 30 |
| Processo | `DELETE/EXTRA` | 0 de 30 (0%; 0%–12%) | 0 · 0 | 30 de 30 |
| Processo | `DELETE/NORMAL` | 0 de 30 (0%; 0%–12%) | 0 · 0 | 30 de 30 |
| Processo | `WAL/FULL` | 0 de 30 (0%; 0%–12%) | 0 · 0 | 30 de 30 |
| Processo | `WAL/NORMAL` | 0 de 30 (0%; 0%–12%) | 0 · 0 | 30 de 30 |
| Sistema | `DELETE/FULL` | 20 de 20 (100%; 83%–100%) | 1 · 1 | 20 de 20 |
| Sistema | `DELETE/EXTRA` | 0 de 20 (0%; 0%–17%) | 0 · 0 | 20 de 20 |
| Sistema | `DELETE/NORMAL` | 19 de 20 (95%; 75%–100%) | 1 · 1 | 20 de 20 |
| Sistema | `WAL/FULL` | 0 de 20 (0%; 0%–17%) | 0 · 0 | 20 de 20 |
| Sistema | `WAL/NORMAL` | 17 de 20 (85%; 62%–97%) | 492 · 868 | 20 de 20 |

**Comparações planejadas** (queda do sistema, teste exato de Fisher unilateral, Holm):

| Comparação | Com perda | p (Holm) | Rejeita H₀? |
| --- | ---: | ---: | :---: |
| WAL/NORMAL perde mais que WAL/FULL | 17/20 × 0/20 | < 0,001 | Sim |
| DELETE/FULL perde mais que DELETE/EXTRA | 20/20 × 0/20 | < 0,001 | Sim |

## 3. Leitura e escrita ao mesmo tempo

A principal promessa do WAL é que leitores e escritor não se bloqueiam. Um processo grava sem parar (1 `INSERT` por transação, como uma sincronização em segundo plano) enquanto outro lê uma tela de 50 linhas a cada 5 ms, durante 3 s. As duas conexões usam o *timeout* padrão do Python (5 s): quem encontra o banco travado espera, como em um app real. 30 blocos; em cada um, as 4 configurações com e sem escritor, em ordem sorteada. O limite de 16 ms é o orçamento de um quadro a 60 Hz.

Cada linha resume os blocos pela mediana (o pior caso é o máximo entre todos). Sem bloqueio, a leitura completa as 600 telas previstas em 3 s.

| Escritor | Configuração | Telas lidas em 3 s (de 600) | Latência mediana | p99 | Pior leitura | Leituras > 16 ms | Escritor (transações/s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Com | `DELETE/FULL` | 8 | 161,02 ms | 1.859,72 ms | 3.982 ms | 67% | 149 |
| Com | `DELETE/NORMAL` | 10 | 122,14 ms | 1.715,87 ms | 3.469 ms | 67% | 214 |
| Com | `WAL/FULL` | 600 | 0,04 ms | 0,09 ms | 3,6 ms | 0% | 476 |
| Com | `WAL/NORMAL` | 600 | 0,05 ms | 0,09 ms | 18 ms | 0% | 33.767 |
| Sem | `DELETE/FULL` | 600 | 0,08 ms | 0,15 ms | 0,5 ms | 0% | — |
| Sem | `DELETE/NORMAL` | 600 | 0,08 ms | 0,15 ms | 0,7 ms | 0% | — |
| Sem | `WAL/FULL` | 600 | 0,04 ms | 0,09 ms | 0,4 ms | 0% | — |
| Sem | `WAL/NORMAL` | 600 | 0,04 ms | 0,09 ms | 1,1 ms | 0% | — |

**Hipóteses registradas antes da coleta** (synchronous = FULL, pareadas por bloco, Wilcoxon unilateral, Holm):

| Hipótese | Comparação | Razão das medianas (IC 95%) | p (Holm) | Rejeita H₀? |
| --- | --- | ---: | ---: | :---: |
| **C-1** Com escrita em andamento, a leitura p99 é menor no WAL | DELETE/FULL ÷ WAL/FULL (`latencia_p99_ms`) | 20.641× [16.195; 28.611] | < 0,001 | Sim |
| **C-2** Com leituras em andamento, o escritor faz mais transações/s no WAL | WAL/FULL ÷ DELETE/FULL (`escritas_por_s`) | 3,19× [3,08; 3,27] | < 0,001 | Sim |

## 4. O que isso muda nas conclusões

1. **Travar o app não perdeu dados em nenhuma configuração** (0 rodadas com perda em 150). O risco do `synchronous` aparece só na queda do sistema ou de energia.
2. **Custo medido do NORMAL:** na queda do sistema, `WAL/NORMAL` perdeu transações confirmadas em 17 de 20 rodadas (até 868 por queda), contra 0 de 20 no `WAL/FULL` (Fisher, p Holm < 0,001). É a contrapartida do ganho de H-3 (168× no Windows e 442× no Linux, onde a queda foi simulada), e a durabilidade deixa de ser só uma citação da documentação.
3. **`DELETE/FULL` (o padrão do Python e do SQLite):** perdeu transação confirmada em 20 de 20 quedas (até 1 por queda); com `DELETE/EXTRA`, 0 de 20 (Fisher, p Holm < 0,001). É o que a documentação descreve para o EXTRA: sincronizar a pasta depois de apagar o journal. O `WAL/FULL` não perdeu nada e grava mais rápido que o `DELETE/FULL` (H-1: 3,16× no Windows e 1,95× no Linux, onde a queda foi simulada).
4. **Integridade:** 250 de 250 bancos passaram no `PRAGMA integrity_check` depois da falha: as perdas são de transações recentes, não corrupção.
5. **Concorrência:** com escrita em segundo plano, o leitor do `DELETE/FULL` completou só 8 das 600 telas em 3 s (latência mediana 161 ms, pior caso 3.982 ms: a tela congelaria), enquanto no `WAL/FULL` completou 600 (pior caso 3,6 ms, dentro de um quadro). C-1 confirmada (p Holm < 0,001); C-2 confirmada (escritor 3,19× no WAL, p Holm < 0,001).
6. **Validade externa:** em 5 ambientes, a direção dos efeitos se repete em 24 de 25 pares e a conclusão em 23 de 25; a magnitude muda de ambiente para ambiente.
