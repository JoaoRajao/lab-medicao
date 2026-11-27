# Dados do Lab05

| Arquivo | Conteúdo |
| --- | --- |
| `raw/piloto.csv` | Piloto da S01 (#119): 5 blocos, 2 cargas, 40 medições. |
| `raw/coleta_completa.csv` | Coleta completa da S02 (#121): 30 blocos × 3 cargas × 4 configurações = 360 medições. |
| `raw/coleta_linux.csv` | Replicação da coleta completa no Ubuntu 26.04 (WSL2, ext4, SQLite 3.46.1), na mesma máquina (#137). |
| `raw/coleta_actions_<sistema>.csv` | Replicação nos runners do GitHub Actions (Ubuntu, Windows, macOS), baixada do artefato do workflow `lab05-replicacao` (#137). |
| `raw/concorrencia.csv` | Leitura e escrita ao mesmo tempo (#137): uma linha por medição, com latências da leitura, leituras acima de 16 ms e vazão do escritor. |
| `raw/durabilidade.csv` | Durabilidade medida (#137): uma linha por falha provocada, com as transações confirmadas, as que sobraram e a integridade do banco. |
| `processed/robustez_*.csv` | Resultados da replicação e da durabilidade, gerados por `python -m labs.lab05_sqlite.robustez`. |
| `raw/*_ambiente.json` | Data da coleta, versões do SQLite e do Python, sistema, processador, disco e parâmetros. |

Uma linha do CSV é uma medição. As colunas estão descritas na seção 3.2 da [proposta](../../../docs/lab05/proposta.md).

## Como a coleta completa foi feita

```bash
python -m labs.lab05_sqlite.coleta --repeticoes 30 --nome coleta_completa   # ~4 min
```

- Uma única máquina (Windows 11, SSD NVMe Samsung), na tomada, com os outros programas fechados.
- **Uma primeira execução foi descartada.** Ela rodou enquanto outros processos usavam o disco e a CPU, o que viola o protocolo. A coleta foi repetida do zero, com a mesma semente, e só a repetição está versionada.
- Os dados não são editados à mão. A validação do desenho (blocos completos, ordem sorteada, tratamentos, coerência entre colunas e ambiente) está em `tests/lab05/test_dados.py`.

## Replicação, durabilidade e concorrência (#137)

```bash
wsl -d Ubuntu --cd <repo> -- python3 -m labs.lab05_sqlite.coleta --repeticoes 30 --nome coleta_linux --pasta /root/lab05_db
python -m labs.lab05_sqlite.durabilidade      # no Windows; derruba o processo e reinicia o Linux do WSL (~30 min)
python -m labs.lab05_sqlite.concorrencia      # leitura e escrita simultâneas (~15 min, máquina ociosa)
gh workflow run lab05-replicacao              # replicação no Actions; depois: gh run download <id>
python -m labs.lab05_sqlite.robustez          # análise e docs/lab05/robustez.md
```

- No WSL, os bancos ficam no ext4 (`/root/...`). O `/tmp` do WSL é `tmpfs` (memória), onde o `fsync` não custa nada e a medição perderia o sentido.
- O disco do Ubuntu é um disco virtual (`.vhdx`) no mesmo SSD NVMe do Windows; por isso o `lsblk` mostra "Virtual Disk".
- A queda do sistema usa `echo b > /proc/sysrq-trigger`. Antes, verificamos que `wsl --terminate` e `wsl --shutdown` gravam o cache no disco (um arquivo escrito sem `fsync` sobreviveu) e por isso não simulam queda de energia; com o `sysrq` o arquivo sumiu.
- Os runners do Actions são máquinas virtuais compartilhadas: servem para conferir a direção dos efeitos, não a magnitude. Os CSVs vêm do artefato do workflow sem edição.
