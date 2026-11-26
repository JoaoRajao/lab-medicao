"""Durabilidade medida (M6) do SQLite por configuracao, com dois tipos de falha (issue #137).

A M6 da proposta vinha so da documentacao. Aqui ela e medida: um processo grava transacoes de 1 INSERT e avisa
cada COMMIT confirmado; no meio das gravacoes provocamos uma falha e contamos quantas transacoes **confirmadas**
sumiram do banco.

    processo: o processo que grava e encerrado a forca (TerminateProcess/SIGKILL), como um app que trava.
              O sistema operacional continua de pe e grava o que ja estava no cache.
    sistema:  o Linux (Ubuntu no WSL2) reinicia na hora com `echo b > /proc/sysrq-trigger`, sem gravar o cache
              nem desmontar o disco. E o metodo usual para simular queda de energia em testes de sistema de
              arquivos. Testamos antes: `wsl --terminate` e `wsl --shutdown` gravam o cache e nao servem.

So conta como perdida uma transacao cujo COMMIT ja tinha retornado e cujo aviso ja tinha chegado ao processo
que controla o teste; por isso o numero de perdidas e um limite inferior, nunca um falso positivo.

    python -m labs.lab05_sqlite.durabilidade                       # no Windows, com o Ubuntu no WSL2 (~30 min)
    python -m labs.lab05_sqlite.durabilidade --rodadas-sistema 0   # so a falha de processo

Atencao: a falha de sistema reinicia a VM do WSL2 inteira (todas as distribuicoes) a cada rodada.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from labs.lab05_sqlite import coleta

SEED = 42
RAIZ = Path(__file__).resolve().parents[2]
DISTRO = "Ubuntu"
PASTA_LINUX = "/root/lab05_durabilidade"  # ext4 do WSL; o /tmp e tmpfs e nao serviria
TAMANHO_PAYLOAD = 200
COLUNAS = ("rodada", "ordem", "falha", "sistema", "journal_mode", "synchronous", "segundos_ate_falha",
           "confirmadas", "presentes", "perdidas", "maior_id_presente", "integridade", "tentativas", "sqlite_version", "seed")
ESPERA = {"processo": (1.0, 3.0), "sistema": (3.0, 8.0)}  # segundos de gravacao antes da falha (sorteados)
# As 4 configuracoes do experimento + DELETE/EXTRA, a correcao que a documentacao indica para o modo DELETE:
# "EXTRA ... the directory containing a rollback journal is synced after that journal is unlinked to commit a
# transaction in DELETE mode" (https://www.sqlite.org/pragma.html#pragma_synchronous).
CONFIGURACOES = (*coleta.CONFIGURACOES, ("DELETE", "EXTRA"))


# ----------------------------------------------------------------- lado que grava e lado que confere o banco
def apagar(banco: Path, tentativas: int = 20) -> None:
    """Apaga o banco e os arquivos auxiliares. No Windows o antivirus pode segurar o arquivo por um instante."""
    for sufixo in ("", "-wal", "-shm", "-journal"):
        arquivo = Path(f"{banco}{sufixo}")
        for _ in range(tentativas):
            try:
                arquivo.unlink(missing_ok=True)
                break
            except PermissionError:
                time.sleep(0.25)


def conectar(banco: Path, journal: str, synchronous: str) -> sqlite3.Connection:
    """Como coleta.conectar (recusa e confere a configuracao), aceitando tambem DELETE/EXTRA."""
    if (journal, synchronous) != ("DELETE", "EXTRA"):
        return coleta.conectar(banco, journal, synchronous)
    con = sqlite3.connect(banco, isolation_level=None)
    modo = con.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
    con.execute("PRAGMA synchronous=EXTRA")
    if modo.upper() != "DELETE" or con.execute("PRAGMA synchronous").fetchone()[0] != 3:
        raise RuntimeError("configuracao DELETE/EXTRA nao aplicada")
    con.execute("CREATE TABLE IF NOT EXISTS evento (id INTEGER PRIMARY KEY, criado REAL, payload TEXT)")
    return con


def boot_id() -> str:
    """Identificador do boot do Linux; muda a cada reinicio (prova de que a queda aconteceu)."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "-"


def escrever(banco: Path, journal: str, synchronous: str) -> None:
    """Grava em passo travado: depois de cada COMMIT imprime o id e espera a resposta de quem controla o teste
    antes da proxima transacao, como um app que grava a cada acao do usuario. Assim o controlador sabe exatamente
    qual foi a ultima transacao confirmada no momento da falha."""
    banco.parent.mkdir(parents=True, exist_ok=True)
    apagar(banco)
    con = conectar(banco, journal, synchronous)
    payload = "x" * TAMANHO_PAYLOAD
    print(f"BOOT {boot_id()}", flush=True)
    i = 0
    while True:
        i += 1
        con.execute("BEGIN")
        con.execute("INSERT INTO evento (id, criado, payload) VALUES (?, ?, ?)", (i, time.time(), payload))
        con.execute("COMMIT")
        print(i, flush=True)
        if not sys.stdin.readline():  # controlador fechou: fim
            return


def conferir(banco: Path, confirmadas: int, tentativas: int = 10) -> dict:
    """Abre o banco depois da falha (o SQLite faz a recuperacao do journal/WAL) e conta o que sobrou.

    No Windows, logo depois de encerrar o processo, o arquivo pode continuar preso por alguns milissegundos (handle
    ainda aberto ou antivirus lendo o -wal) e a abertura falha com "disk I/O error". So esse erro e repetido; a
    coluna `tentativas` registra quantas foram necessarias, e qualquer outro erro vai para o resultado."""
    for tentativa in range(1, tentativas + 1):
        resultado = _conferir(banco, confirmadas)
        if "disk I/O error" not in resultado["integridade"] or tentativa == tentativas:
            return {**resultado, "tentativas": tentativa}
        time.sleep(0.5)
    raise AssertionError("inalcancavel")


def _conferir(banco: Path, confirmadas: int) -> dict:
    resultado = {"presentes": 0, "perdidas": confirmadas, "maior_id_presente": 0, "integridade": "sem banco"}
    if not banco.exists():
        return resultado
    try:
        con = sqlite3.connect(banco)
        try:
            integridade = con.execute("PRAGMA integrity_check").fetchone()[0]
            existe = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'evento'").fetchone()
            presentes, maior = 0, 0
            if existe:
                presentes = con.execute("SELECT count(*) FROM evento WHERE id <= ?", (confirmadas,)).fetchone()[0]
                maior = con.execute("SELECT coalesce(max(id), 0) FROM evento").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as erro:
        resultado["integridade"] = f"erro: {erro}"
        return resultado
    return {"presentes": presentes, "perdidas": confirmadas - presentes, "maior_id_presente": maior,
            "integridade": integridade}


# ----------------------------------------------------------------------------------- controle das rodadas
class Leitor(threading.Thread):
    """Recebe os avisos de COMMIT e libera a proxima transacao, ate o controlador mandar parar."""

    def __init__(self, proc: subprocess.Popen):
        super().__init__(daemon=True)
        self.proc, self.ultimo, self.boot = proc, 0, "-"
        self.primeiro, self.parar = threading.Event(), threading.Event()

    def run(self) -> None:
        try:
            for linha in self.proc.stdout:
                linha = linha.strip()
                if linha.startswith("BOOT "):
                    self.boot = linha[5:]
                elif linha.isdigit():
                    self.ultimo = int(linha)  # o COMMIT dessa transacao ja retornou
                    self.primeiro.set()
                    if self.parar.is_set():
                        return  # sem resposta: o processo fica parado logo depois de confirmar
                    self.proc.stdin.write("\n")
                    self.proc.stdin.flush()
        except (OSError, ValueError):
            return  # o processo morreu


def _gravar_ate_falhar(comando: list[str], espera: float, derrubar) -> tuple[int, float, str]:
    proc = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, bufsize=1)
    leitor = Leitor(proc)
    leitor.start()
    if not leitor.primeiro.wait(60):
        proc.kill()
        raise RuntimeError(f"o processo nao comecou a gravar: {proc.stderr.read()[:500]}")
    inicio = time.perf_counter()
    time.sleep(espera)
    leitor.parar.set()
    leitor.join(timeout=30)  # depois do proximo aviso o processo fica parado, com tudo confirmado
    confirmadas = leitor.ultimo
    derrubar(proc)
    decorrido = time.perf_counter() - inicio
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
    return confirmadas, decorrido, leitor.boot


def _modulo(*args: str) -> list[str]:
    return ["-m", "labs.lab05_sqlite.durabilidade", *args]


def rodada_processo(journal: str, synchronous: str, espera: float, pasta: Path, rodada: int) -> dict:
    banco = pasta / f"processo_{rodada}_{journal}_{synchronous}.db"
    comando = [sys.executable, *_modulo("escrever", "--banco", str(banco), "--journal", journal,
                                        "--synchronous", synchronous)]
    confirmadas, decorrido, _ = _gravar_ate_falhar(comando, espera, lambda p: p.kill())
    resultado = conferir(banco, confirmadas)
    apagar(banco)
    return {"sistema": platform.system(), "segundos_ate_falha": round(decorrido, 3), "confirmadas": confirmadas,
            **resultado, "sqlite_version": sqlite3.sqlite_version}


def _wsl(*args: str, usuario: str = "root", cd: bool = True) -> list[str]:
    base = ["wsl.exe", "-d", DISTRO, "-u", usuario]
    if cd:
        base += ["--cd", _caminho_wsl(RAIZ)]
    return [*base, "--", *args]


def _caminho_wsl(caminho: Path) -> str:
    unidade, resto = caminho.drive, caminho.as_posix()[len(caminho.drive):]
    return f"/mnt/{unidade.rstrip(':').lower()}{resto}"


def _esperar_wsl(limite_s: float = 120) -> None:
    """Depois do reinicio, espera a VM voltar a responder."""
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        if subprocess.run(_wsl("true", cd=False), capture_output=True, timeout=60).returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("o WSL nao voltou depois da queda")


def _queda_de_energia(_proc) -> None:
    try:
        subprocess.run(_wsl("sh", "-c", "echo 1 > /proc/sys/kernel/sysrq; echo b > /proc/sysrq-trigger", cd=False),
                       capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        pass  # a VM caiu antes de responder; o efeito ja aconteceu


def rodada_sistema(journal: str, synchronous: str, espera: float) -> dict:
    banco = f"{PASTA_LINUX}/sistema_{journal}_{synchronous}.db"
    comando = _wsl("python3", *_modulo("escrever", "--banco", banco, "--journal", journal,
                                       "--synchronous", synchronous))
    confirmadas, decorrido, boot_antes = _gravar_ate_falhar(comando, espera, _queda_de_energia)
    _esperar_wsl()
    saida = subprocess.run(_wsl("python3", *_modulo("conferir", "--banco", banco, "--confirmadas",
                                                    str(confirmadas), "--apagar")),
                           capture_output=True, text=True, timeout=120, check=True).stdout
    resultado = json.loads(saida.strip().splitlines()[-1])
    if resultado.pop("boot") == boot_antes:
        raise RuntimeError("o Linux nao reiniciou: a rodada nao simulou a queda")
    return {"sistema": "Linux (WSL2)", "segundos_ate_falha": round(decorrido, 3), "confirmadas": confirmadas,
            **resultado}


def experimento(rodadas: dict[str, int], seed: int = SEED, progresso=print) -> list[dict]:
    """Rodadas em blocos: cada bloco tem as 4 configuracoes em ordem sorteada, e a espera ate a falha tambem e
    sorteada, para que a falha caia em momentos diferentes do ciclo de gravacao do sistema operacional."""
    rng = random.Random(seed)
    linhas = []
    with tempfile.TemporaryDirectory(prefix="lab05_dur_", ignore_cleanup_errors=True) as tmp:
        for falha, n in rodadas.items():
            for rodada in range(1, n + 1):
                ordem = list(CONFIGURACOES)
                rng.shuffle(ordem)
                for posicao, (journal, synchronous) in enumerate(ordem, start=1):
                    espera = rng.uniform(*ESPERA[falha])
                    if falha == "processo":
                        r = rodada_processo(journal, synchronous, espera, Path(tmp), rodada)
                    else:
                        r = rodada_sistema(journal, synchronous, espera)
                    linhas.append({"rodada": rodada, "ordem": posicao, "falha": falha, "journal_mode": journal,
                                   "synchronous": synchronous, **r, "seed": seed})
                    progresso(f"   {falha} {rodada}/{n} {journal}/{synchronous}: "
                              f"{r['perdidas']} de {r['confirmadas']} perdidas ({r['integridade']})")
    return linhas


def ambiente_linux() -> dict:
    saida = subprocess.run(_wsl("python3", *_modulo("ambiente")), capture_output=True, text=True, timeout=120,
                           check=True).stdout
    return json.loads(saida.strip().splitlines()[-1])


def _ambiente_local() -> dict:
    return {"sqlite_version": sqlite3.sqlite_version, "python": sys.version.split()[0],
            "sistema": platform.platform(), "processador": platform.processor() or platform.machine(),
            "discos": coleta.discos()}


def salvar(linhas: list[dict], info: dict, nome: str = "durabilidade", destino: Path = coleta.DADOS) -> Path:
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
    parser = argparse.ArgumentParser(description="Durabilidade medida do SQLite (Lab05, #137)")
    sub = parser.add_subparsers(dest="acao")
    e = sub.add_parser("escrever", help="(uso interno) grava ate ser interrompido")
    e.add_argument("--banco", type=Path, required=True)
    e.add_argument("--journal", required=True)
    e.add_argument("--synchronous", required=True)
    c = sub.add_parser("conferir", help="(uso interno) conta as transacoes que sobraram")
    c.add_argument("--banco", type=Path, required=True)
    c.add_argument("--confirmadas", type=int, required=True)
    c.add_argument("--apagar", action="store_true")
    sub.add_parser("ambiente", help="(uso interno) versoes do lado Linux")
    parser.add_argument("--rodadas-processo", type=int, default=30)
    parser.add_argument("--rodadas-sistema", type=int, default=20)
    parser.add_argument("--nome", default="durabilidade")
    args = parser.parse_args(argv)

    if args.acao == "escrever":
        escrever(args.banco, args.journal, args.synchronous)
        return 0
    if args.acao == "conferir":
        resultado = conferir(args.banco, args.confirmadas)
        resultado["sqlite_version"] = sqlite3.sqlite_version
        resultado["boot"] = boot_id()
        if args.apagar:
            apagar(args.banco)
        print(json.dumps(resultado))
        return 0
    if args.acao == "ambiente":
        print(json.dumps(_ambiente_local()))
        return 0

    rodadas = {"processo": args.rodadas_processo, "sistema": args.rodadas_sistema}
    rodadas = {k: v for k, v in rodadas.items() if v > 0}
    info = {"coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": SEED,
            "rodadas": rodadas, "espera_s": ESPERA, "tamanho_payload": TAMANHO_PAYLOAD,
            "processo": _ambiente_local()}
    if "sistema" in rodadas:
        info["sistema"] = {**ambiente_linux(), "metodo": "echo b > /proc/sysrq-trigger (reinicio sem sync)",
                           "pasta": PASTA_LINUX}
    print(f"Durabilidade: {rodadas} rodadas x {len(CONFIGURACOES)} configuracoes")
    caminho = salvar(experimento(rodadas), info, args.nome)
    print(f"   dados em {caminho}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
