"""Coleta do Lab05: desempenho do SQLite por configuracao de journal e de sincronizacao (issue #119).

Experimento fatorial 2 x 2 rodado na maquina do grupo, sem sistema de terceiros:
    journal_mode in {DELETE, WAL}  x  synchronous in {FULL, NORMAL}
em duas cargas:
    escrita: N transacoes, cada uma com 1 INSERT e COMMIT (padrao de apps que gravam a cada acao do usuario);
    leitura: K consultas por chave primaria em uma tabela ja populada.

Cada repeticao e um bloco com as 4 configuracoes em ordem aleatoria (semente fixa), cada uma em um arquivo de
banco novo, para que deriva da maquina (temperatura, cache do SO, processos em segundo plano) afete todas igualmente.

    python -m labs.lab05_sqlite.coleta --piloto          # 5 blocos, cargas pequenas (S01)
    python -m labs.lab05_sqlite.coleta --repeticoes 30   # coleta completa (S02)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import sqlite3
import statistics
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

SEED = 42
JOURNAL = ("DELETE", "WAL")
SYNCHRONOUS = ("FULL", "NORMAL")
CONFIGURACOES = tuple((j, s) for j in JOURNAL for s in SYNCHRONOUS)
CARGAS = ("escrita", "leitura")
DADOS = Path(__file__).resolve().parent / "data" / "raw"
COLUNAS = ("bloco", "ordem", "carga", "journal_mode", "synchronous", "operacoes", "duracao_s",
           "ops_por_s", "latencia_mediana_ms", "latencia_p95_ms", "sqlite_version", "seed")


@dataclass(frozen=True)
class Parametros:
    repeticoes: int = 30
    escritas: int = 500       # transacoes de 1 INSERT por medicao
    linhas_leitura: int = 20_000
    leituras: int = 5_000     # SELECT por chave primaria por medicao
    tamanho_payload: int = 200  # bytes de texto por linha
    seed: int = SEED


PILOTO = Parametros(repeticoes=5, escritas=200, linhas_leitura=5_000, leituras=2_000)


def conectar(caminho: Path, journal: str, synchronous: str) -> sqlite3.Connection:
    if journal not in JOURNAL or synchronous not in SYNCHRONOUS:  # o SQLite ignora PRAGMA invalido em silencio
        raise ValueError(f"configuracao fora do experimento: journal={journal}, synchronous={synchronous}")
    con = sqlite3.connect(caminho, isolation_level=None)  # autocommit: controlamos BEGIN/COMMIT
    modo = con.execute(f"PRAGMA journal_mode={journal}").fetchone()[0]
    con.execute(f"PRAGMA synchronous={synchronous}")
    efetivo = con.execute("PRAGMA synchronous").fetchone()[0]
    if modo.upper() != journal or efetivo != {"FULL": 2, "NORMAL": 1}[synchronous]:
        raise RuntimeError(f"configuracao nao aplicada: journal={modo}, synchronous={efetivo}")
    con.execute("CREATE TABLE IF NOT EXISTS evento (id INTEGER PRIMARY KEY, criado REAL, payload TEXT)")
    return con


def _percentil(valores: list[float], q: float) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(q * (len(ordenados) - 1))))]


def medir_escrita(con: sqlite3.Connection, p: Parametros, rng: random.Random) -> list[float]:
    """Latencia (s) de cada transacao com 1 INSERT + COMMIT."""
    payloads = ["".join(rng.choices("abcdefghij", k=p.tamanho_payload)) for _ in range(p.escritas)]
    latencias = []
    for payload in payloads:
        inicio = time.perf_counter()
        con.execute("BEGIN")
        con.execute("INSERT INTO evento (criado, payload) VALUES (?, ?)", (time.time(), payload))
        con.execute("COMMIT")
        latencias.append(time.perf_counter() - inicio)
    return latencias


def medir_leitura(con: sqlite3.Connection, p: Parametros, rng: random.Random) -> list[float]:
    """Popula a tabela (fora da medicao) e mede SELECTs por chave primaria aleatoria."""
    con.execute("BEGIN")
    con.executemany("INSERT INTO evento (criado, payload) VALUES (?, ?)",
                    ((0.0, "x" * p.tamanho_payload) for _ in range(p.linhas_leitura)))
    con.execute("COMMIT")
    chaves = [rng.randint(1, p.linhas_leitura) for _ in range(p.leituras)]
    latencias = []
    for chave in chaves:
        inicio = time.perf_counter()
        con.execute("SELECT payload FROM evento WHERE id = ?", (chave,)).fetchone()
        latencias.append(time.perf_counter() - inicio)
    return latencias


def medir(carga: str, journal: str, synchronous: str, p: Parametros, rng: random.Random, pasta: Path) -> dict:
    caminho = pasta / f"{carga}_{journal}_{synchronous}.db"
    con = conectar(caminho, journal, synchronous)
    try:
        latencias = (medir_escrita if carga == "escrita" else medir_leitura)(con, p, rng)
    finally:
        con.close()
    for sufixo in ("", "-wal", "-shm", "-journal"):  # cada medicao comeca com banco novo
        Path(f"{caminho}{sufixo}").unlink(missing_ok=True)
    duracao = sum(latencias)
    return {"carga": carga, "journal_mode": journal, "synchronous": synchronous, "operacoes": len(latencias),
            "duracao_s": round(duracao, 6), "ops_por_s": round(len(latencias) / duracao, 2),
            "latencia_mediana_ms": round(1000 * statistics.median(latencias), 4),
            "latencia_p95_ms": round(1000 * _percentil(latencias, 0.95), 4)}


def coletar(p: Parametros, pasta: Path | None = None, progresso=print) -> list[dict]:
    rng = random.Random(p.seed)
    linhas = []
    with tempfile.TemporaryDirectory(prefix="lab05_", dir=pasta) as tmp:
        for bloco in range(1, p.repeticoes + 1):
            ordem = [(c, j, s) for c in CARGAS for j, s in CONFIGURACOES]
            rng.shuffle(ordem)
            for posicao, (carga, journal, synchronous) in enumerate(ordem, start=1):
                linha = medir(carga, journal, synchronous, p, rng, Path(tmp))
                linhas.append({"bloco": bloco, "ordem": posicao, **linha,
                               "sqlite_version": sqlite3.sqlite_version, "seed": p.seed})
            progresso(f"   bloco {bloco}/{p.repeticoes}")
    return linhas


def ambiente(p: Parametros) -> dict:
    return {"coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sqlite_version": sqlite3.sqlite_version, "python": sys.version.split()[0],
            "sistema": platform.platform(), "processador": platform.processor() or platform.machine(),
            "cpus": os.cpu_count(), "parametros": asdict(p)}


def salvar(linhas: list[dict], info: dict, nome: str, destino: Path = DADOS) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{nome}.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)
    (destino / f"{nome}_ambiente.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    return caminho


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coleta do Lab05 (SQLite: journal_mode x synchronous)")
    parser.add_argument("--piloto", action="store_true", help="5 blocos com cargas pequenas (S01)")
    parser.add_argument("--repeticoes", type=int, default=Parametros.repeticoes)
    parser.add_argument("--nome", help="Nome do CSV em data/raw (padrao: piloto ou coleta_<data>)")
    args = parser.parse_args(argv)
    p = PILOTO if args.piloto else Parametros(repeticoes=args.repeticoes)
    nome = args.nome or ("piloto" if args.piloto else f"coleta_{datetime.now():%Y-%m-%d}")
    print(f"SQLite {sqlite3.sqlite_version}: {p.repeticoes} blocos x {len(CARGAS) * len(CONFIGURACOES)} medicoes")
    caminho = salvar(coletar(p), ambiente(p), nome)
    print(f"   dados em {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
