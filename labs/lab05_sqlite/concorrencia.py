"""Leitura e escrita ao mesmo tempo: a principal promessa do WAL (issue #137).

A documentacao diz que no WAL "readers do not block writers and a writer does not block readers"
(https://www.sqlite.org/wal.html). O experimento principal mediu leitura e escrita separadas e nao testa isso.

Cenario de app: um processo grava sem parar (sincronizacao em segundo plano, 1 INSERT por transacao) enquanto
outro le uma "tela" de 50 linhas a cada 5 ms (como uma lista rolando). Cada leitura tem o orcamento de um quadro
a 60 Hz, 16 ms (https://developer.android.com/topic/performance/vitals/render). As duas conexoes usam o timeout
padrao do Python (5 s): quem encontra o banco travado espera, em vez de falhar, como em um app real.

Desenho: 30 blocos; em cada bloco, as 4 configuracoes x {com escritor, sem escritor} em ordem sorteada (semente 42),
banco novo por medicao. A condicao sem escritor e a linha de base de cada configuracao.

Hipoteses, registradas antes da coleta (comparacoes com synchronous = FULL, pareadas por bloco, Wilcoxon, Holm):
    C-1: com escrita em andamento, a latencia p99 das leituras e menor no WAL do que no DELETE.
    C-2: com leituras em andamento, o escritor conclui mais transacoes por segundo no WAL do que no DELETE.
Descritivo: fracao de leituras acima de 16 ms e quanto o escritor piora a leitura em cada configuracao.

    python -m labs.lab05_sqlite.concorrencia                 # ~15 min, com a maquina ociosa
    python -m labs.lab05_sqlite.concorrencia --repeticoes 2  # teste rapido
    python3 concorrencia.py --threads                        # iPhone (a-Shell), ao lado de coleta.py
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

try:
    from labs.lab05_sqlite import coleta
except ImportError:  # rodando solto, ao lado de coleta.py (ex.: no iPhone)
    import coleta

SEED = 42
LINHAS = 20_000          # tabela populada antes da medicao
TELA = 50                # linhas por leitura (uma tela de lista)
INTERVALO_S = 0.005      # uma leitura a cada 5 ms
DURACAO_S = 3.0          # tempo de leitura por medicao
QUADRO_MS = 16.0         # orcamento de um quadro a 60 Hz
TAMANHO_PAYLOAD = 200
COLUNAS = ("bloco", "ordem", "journal_mode", "synchronous", "escritor", "leituras", "erros_leitura",
           "latencia_mediana_ms", "latencia_p95_ms", "latencia_p99_ms", "latencia_max_ms", "acima_quadro",
           "escritas", "escritas_por_s", "erros_escrita", "sqlite_version", "seed")


def _percentil(valores: list[float], q: float) -> float:
    return coleta._percentil(valores, q)


# ------------------------------------------------------------------------------------- processo que escreve
def escritor(banco: Path, journal: str, synchronous: str, duracao: float, avisar=None) -> dict:
    """Grava 1 INSERT por transacao durante `duracao` segundos; avisa PRONTO depois do primeiro COMMIT."""
    avisar = avisar or (lambda: print("PRONTO", flush=True))
    con = coleta.conectar(banco, journal, synchronous)
    payload = "w" * TAMANHO_PAYLOAD
    escritas = erros = 0
    fim = None
    while fim is None or time.perf_counter() < fim:
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO evento (criado, payload) VALUES (?, ?)", (time.time(), payload))
            con.execute("COMMIT")
            escritas += 1
        except sqlite3.OperationalError:
            erros += 1
            if con.in_transaction:
                con.execute("ROLLBACK")
        if fim is None:
            avisar()
            inicio, fim = time.perf_counter(), time.perf_counter() + duracao
    con.close()
    return {"escritas": escritas, "escritas_por_s": escritas / (time.perf_counter() - inicio),
            "erros_escrita": erros}


# -------------------------------------------------------------------------------------------- medicao
def preparar(banco: Path, journal: str, synchronous: str) -> None:
    con = coleta.conectar(banco, journal, synchronous)
    con.execute("BEGIN")
    con.executemany("INSERT INTO evento (criado, payload) VALUES (0, ?)",
                    (("x" * TAMANHO_PAYLOAD,) for _ in range(LINHAS)))
    con.execute("COMMIT")
    con.close()


def ler(con: sqlite3.Connection, rng: random.Random, duracao: float) -> tuple[list[float], int]:
    latencias, erros = [], 0
    proxima = time.perf_counter()
    fim = proxima + duracao
    while time.perf_counter() < fim:
        inicio_tela = rng.randint(1, LINHAS - TELA)
        t0 = time.perf_counter()
        try:
            con.execute("SELECT id, payload FROM evento WHERE id BETWEEN ? AND ?",
                        (inicio_tela, inicio_tela + TELA - 1)).fetchall()
            latencias.append(time.perf_counter() - t0)
        except sqlite3.OperationalError:
            erros += 1
        proxima += INTERVALO_S
        espera = proxima - time.perf_counter()
        if espera > 0:
            time.sleep(espera)
    return latencias, erros


def medir(journal: str, synchronous: str, com_escritor: bool, rng: random.Random, pasta: Path,
          bloco: int, modo: str = "processo") -> dict:
    banco = pasta / f"conc_{bloco}_{journal}_{synchronous}_{int(com_escritor)}.db"
    preparar(banco, journal, synchronous)
    leitor = coleta.conectar(banco, journal, synchronous)
    proc = fio = None
    resultado: dict = {}
    if com_escritor and modo == "thread":
        # iOS nao permite iniciar processos: o escritor roda em uma thread com conexao propria. O modulo sqlite3
        # libera o GIL durante as chamadas ao SQLite, entao leitura e escrita andam ao mesmo tempo.
        pronto = threading.Event()
        fio = threading.Thread(target=lambda: resultado.update(
            escritor(banco, journal, synchronous, DURACAO_S + 1.0, pronto.set)), daemon=True)
        fio.start()
        if not pronto.wait(60):
            raise RuntimeError("escritor (thread) nao comecou")
    elif com_escritor:
        proc = subprocess.Popen([sys.executable, "-m", "labs.lab05_sqlite.concorrencia", "escritor",
                                 "--banco", str(banco), "--journal", journal, "--synchronous", synchronous,
                                 "--duracao", str(DURACAO_S + 1.0)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.stdout.readline().strip() != "PRONTO":
            raise RuntimeError(f"escritor nao comecou: {proc.stderr.read()[:500]}")
    latencias, erros = ler(leitor, rng, DURACAO_S)
    leitor.close()
    escrita = {"escritas": 0, "escritas_por_s": 0.0, "erros_escrita": 0}
    if fio:
        fio.join(timeout=120)
        escrita = resultado
    if proc:
        saida, erro = proc.communicate(timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"escritor falhou: {erro[:500]}")
        escrita = json.loads(saida.strip().splitlines()[-1])
    for sufixo in ("", "-wal", "-shm", "-journal"):
        Path(f"{banco}{sufixo}").unlink(missing_ok=True)
    ms = [1000 * x for x in latencias]
    return {"journal_mode": journal, "synchronous": synchronous, "escritor": "sim" if com_escritor else "nao",
            "leituras": len(ms), "erros_leitura": erros,
            "latencia_mediana_ms": round(statistics.median(ms), 4), "latencia_p95_ms": round(_percentil(ms, 0.95), 4),
            "latencia_p99_ms": round(_percentil(ms, 0.99), 4), "latencia_max_ms": round(max(ms), 4),
            "acima_quadro": sum(x > QUADRO_MS for x in ms),
            "escritas": escrita["escritas"], "escritas_por_s": round(escrita["escritas_por_s"], 2),
            "erros_escrita": escrita["erros_escrita"]}


def coletar(repeticoes: int, seed: int = SEED, progresso=print, modo: str = "processo") -> list[dict]:
    rng = random.Random(seed)
    linhas = []
    with tempfile.TemporaryDirectory(prefix="lab05_conc_", ignore_cleanup_errors=True) as tmp:
        for bloco in range(1, repeticoes + 1):
            ordem = [(j, s, e) for j, s in coleta.CONFIGURACOES for e in (True, False)]
            rng.shuffle(ordem)
            for posicao, (journal, synchronous, com_escritor) in enumerate(ordem, start=1):
                linha = medir(journal, synchronous, com_escritor, rng, Path(tmp), bloco, modo)
                linhas.append({"bloco": bloco, "ordem": posicao, **linha,
                               "sqlite_version": sqlite3.sqlite_version, "seed": seed})
            progresso(f"   bloco {bloco}/{repeticoes}")
    return linhas


def salvar(linhas: list[dict], nome: str, destino: Path = coleta.DADOS, repeticoes: int = 0,
           modo: str = "processo") -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{nome}.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor_csv = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        escritor_csv.writeheader()
        escritor_csv.writerows(linhas)
    info = coleta.ambiente(coleta.Parametros(repeticoes=repeticoes))
    info["parametros"] = {"repeticoes": repeticoes, "linhas": LINHAS, "tela": TELA, "intervalo_s": INTERVALO_S,
                          "duracao_s": DURACAO_S, "quadro_ms": QUADRO_MS, "timeout_s": 5.0, "seed": SEED,
                          "escritor": modo}
    (destino / f"{nome}_ambiente.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    return caminho


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Leitura e escrita ao mesmo tempo (Lab05, #137)")
    sub = parser.add_subparsers(dest="acao")
    e = sub.add_parser("escritor", help="(uso interno) processo que grava")
    e.add_argument("--banco", type=Path, required=True)
    e.add_argument("--journal", required=True)
    e.add_argument("--synchronous", required=True)
    e.add_argument("--duracao", type=float, required=True)
    parser.add_argument("--repeticoes", type=int, default=30)
    parser.add_argument("--nome", default="concorrencia")
    parser.add_argument("--threads", action="store_true",
                        help="escritor em thread em vez de processo (para o iOS, que nao permite processos)")
    args = parser.parse_args(argv)
    if args.acao == "escritor":
        print(json.dumps(escritor(args.banco, args.journal, args.synchronous, args.duracao)))
        return 0
    print(f"Concorrencia: {args.repeticoes} blocos x {2 * len(coleta.CONFIGURACOES)} medicoes")
    modo = "thread" if args.threads else "processo"
    caminho = salvar(coletar(args.repeticoes, modo=modo), args.nome, repeticoes=args.repeticoes, modo=modo)
    print(f"   dados em {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
