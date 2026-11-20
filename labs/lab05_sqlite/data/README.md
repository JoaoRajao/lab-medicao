# Dados do Lab05

| Arquivo | Conteúdo |
| --- | --- |
| `raw/piloto.csv` | Piloto da S01 (#119): 5 blocos, 2 cargas, 40 medições. |
| `raw/coleta_completa.csv` | Coleta completa da S02 (#121): 30 blocos × 3 cargas × 4 configurações = 360 medições. |
| `raw/*_ambiente.json` | Data da coleta, versões do SQLite e do Python, sistema, processador, disco e parâmetros. |

Uma linha do CSV é uma medição. As colunas estão descritas na seção 3.2 da [proposta](../../../docs/lab05/proposta.md).

## Como a coleta completa foi feita

```bash
python -m labs.lab05_sqlite.coleta --repeticoes 30 --nome coleta_completa   # ~4 min
```

- Uma única máquina (Windows 11, SSD NVMe Samsung), na tomada, com os outros programas fechados.
- **Uma primeira execução foi descartada.** Ela rodou enquanto outros processos usavam o disco e a CPU, o que viola o protocolo. A coleta foi repetida do zero, com a mesma semente, e só a repetição está versionada.
- Os dados não são editados à mão. A validação do desenho (blocos completos, ordem sorteada, tratamentos, coerência entre colunas e ambiente) está em `tests/lab05/test_dados.py`.
