from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from labs.lab05_sqlite import coleta, durabilidade, robustez


# ----------------------------------------------------------------------------------------------- durabilidade
def test_conectar_aceita_delete_extra_e_confere(tmp_path):
    con = durabilidade.conectar(tmp_path / "x.db", "DELETE", "EXTRA")
    assert con.execute("PRAGMA synchronous").fetchone()[0] == 3
    con.close()
    with pytest.raises(ValueError):
        durabilidade.conectar(tmp_path / "y.db", "WAL", "EXTRA")  # fora do experimento


def test_conferir_conta_so_as_confirmadas_que_sumiram(tmp_path):
    banco = tmp_path / "b.db"
    con = coleta.conectar(banco, "WAL", "FULL")
    con.executemany("INSERT INTO evento (id, criado, payload) VALUES (?, 0, 'x')", [(i,) for i in (1, 2, 3, 5, 6)])
    con.close()
    r = durabilidade.conferir(banco, confirmadas=5)
    assert r == {"presentes": 4, "perdidas": 1, "maior_id_presente": 6, "integridade": "ok", "tentativas": 1}
    assert durabilidade.conferir(tmp_path / "nao_existe.db", 3)["perdidas"] == 3


def test_escritor_em_passo_travado_nao_perde_nada_quando_o_processo_morre(tmp_path):
    banco = tmp_path / "p.db"
    comando = [sys.executable, "-m", "labs.lab05_sqlite.durabilidade", "escrever", "--banco", str(banco),
               "--journal", "WAL", "--synchronous", "NORMAL"]
    confirmadas, _, _ = durabilidade._gravar_ate_falhar(comando, 0.3, lambda p: p.kill())
    assert confirmadas > 0
    r = durabilidade.conferir(banco, confirmadas)
    assert r["perdidas"] == 0 and r["integridade"] == "ok"
    assert r["maior_id_presente"] in (confirmadas, confirmadas + 1)  # parado logo depois de confirmar
    durabilidade.apagar(banco)


def test_caminho_wsl():
    assert durabilidade._caminho_wsl(Path("C:/Users/a/repo")) == "/mnt/c/Users/a/repo"


# --------------------------------------------------------------------------------------------- replicacao
def _coleta(fatores: dict, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    linhas = []
    for bloco in range(1, 31):
        for (carga, j, s), v in fatores.items():
            linhas.append({"bloco": bloco, "carga": carga, "journal_mode": j, "synchronous": s,
                           "ops_por_s": v * float(np.exp(rng.normal(0, 0.03))), "sqlite_version": "x"})
    return pd.DataFrame(linhas)


BASE = {("escrita", "DELETE", "FULL"): 100, ("escrita", "DELETE", "NORMAL"): 140, ("escrita", "WAL", "FULL"): 300,
        ("escrita", "WAL", "NORMAL"): 50_000, ("leitura", "DELETE", "FULL"): 50_000,
        ("leitura", "WAL", "FULL"): 250_000, ("leitura_transacao", "DELETE", "FULL"): 400_000,
        ("leitura_transacao", "WAL", "FULL"): 400_000}


def test_replicacao_compara_direcao_e_conclusao_entre_ambientes():
    linux = dict(BASE) | {("escrita", "WAL", "FULL"): 200}  # efeito menor, mesma direcao
    coletas = pd.concat([_coleta(BASE, 1).assign(ambiente=robustez.REFERENCIA),
                         _coleta(linux, 2).assign(ambiente="Outro")])
    rep = robustez.replicacao(coletas)
    assert len(rep) == 2 * len(robustez.COMPARACOES)
    assert rep.loc[rep["confirmatoria"], "p_holm"].notna().all() and rep.loc[~rep["confirmatoria"], "p_holm"].isna().all()
    h1 = rep[rep["codigo"] == "H-1"].set_index("ambiente")["razao"]
    assert h1[robustez.REFERENCIA] == pytest.approx(3, rel=0.05) and h1["Outro"] == pytest.approx(2, rel=0.05)
    comp = robustez.comparar_ambientes(rep).set_index("codigo")
    assert comp.loc["H-1", "ambientes"] == 2 and comp.loc["H-1", "mesma_direcao"] == 2
    assert comp.loc["H-1", "mesma_conclusao"] == 2
    assert not rep[(rep["codigo"] == "E-1")]["rejeita_h0"].any()  # sem efeito na leitura em transacao


def test_holm():
    assert robustez.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


# --------------------------------------------------------------------------------- resumo da durabilidade
def _durabilidade() -> pd.DataFrame:
    linhas = []
    perdas = {("DELETE", "FULL"): [1] * 8 + [0] * 12, ("DELETE", "EXTRA"): [0] * 20,
              ("DELETE", "NORMAL"): [1] * 10 + [0] * 10, ("WAL", "FULL"): [0] * 20,
              ("WAL", "NORMAL"): [30] * 15 + [0] * 5}
    for (j, s), lista in perdas.items():
        for rodada, perdidas in enumerate(lista, start=1):
            linhas.append({"rodada": rodada, "falha": "sistema", "journal_mode": j, "synchronous": s,
                           "confirmadas": 1000, "perdidas": perdidas, "integridade": "ok"})
            linhas.append({"rodada": rodada, "falha": "processo", "journal_mode": j, "synchronous": s,
                           "confirmadas": 1000, "perdidas": 0, "integridade": "ok"})
    return pd.DataFrame(linhas)


def _dados(dur: pd.DataFrame, conc: pd.DataFrame | None = None) -> dict:
    rep = pd.DataFrame({"ambiente": [robustez.REFERENCIA] * 2, "codigo": ["H-1", "H-3"], "razao": [3.16, 168.3]})
    d = {"durabilidade": robustez.resumo_durabilidade(dur), "testes": robustez.testes_durabilidade(dur),
         "comparacao": pd.DataFrame({"ambientes": [5], "mesma_direcao": [5], "mesma_conclusao": [5]}),
         "replicacao": rep}
    if conc is not None:
        d["concorrencia"], d["testes_concorrencia"] = (robustez.resumo_concorrencia(conc),
                                                       robustez.testes_concorrencia(conc))
    return d


def test_resumo_e_testes_da_durabilidade():
    dur = _durabilidade()
    resumo = robustez.resumo_durabilidade(dur)
    assert list(resumo["falha"].unique()) == ["processo", "sistema"]
    wn = resumo[(resumo["falha"] == "sistema") & (resumo["journal_mode"] == "WAL") & (resumo["synchronous"] == "NORMAL")]
    assert wn["rodadas_com_perda"].item() == 15 and wn["ic_inf"].item() < 0.75 < wn["ic_sup"].item()
    assert robustez.testes_durabilidade(dur)["rejeita_h0"].all()
    texto = "\n".join(robustez.conclusoes(_dados(dur)))
    assert "não perdeu dados em nenhuma configuração" in texto and "168×" in texto and "3,16×" in texto
    assert "É o que a documentação descreve" in texto


def test_sem_perda_no_extra_e_frase_condicional():
    dur = _durabilidade()
    dur.loc[(dur["journal_mode"] == "DELETE") & (dur["synchronous"] == "EXTRA") & (dur["rodada"] == 1)
            & (dur["falha"] == "sistema"), "perdidas"] = 1
    texto = "\n".join(robustez.conclusoes(_dados(dur)))
    assert "É o que a documentação descreve" not in texto  # o EXTRA perdeu uma: a frase nao pode aparecer


# --------------------------------------------------------------------------------------------- concorrencia
def _concorrencia(seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    linhas = []
    for bloco in range(1, 31):
        for j, s in coleta.CONFIGURACOES:
            for escritor in ("sim", "nao"):
                travado = j == "DELETE" and escritor == "sim"
                p99 = (300 if travado else 0.2) * float(np.exp(rng.normal(0, 0.1)))
                linhas.append({"bloco": bloco, "journal_mode": j, "synchronous": s, "escritor": escritor,
                               "leituras": 40 if travado else 600, "erros_leitura": 0,
                               "latencia_mediana_ms": p99 / 3, "latencia_p99_ms": p99, "latencia_max_ms": p99 * 1.2,
                               "acima_quadro": 35 if travado else 0,
                               "escritas_por_s": (0 if escritor == "nao" else (90 if j == "DELETE" else 400))
                               * float(np.exp(rng.normal(0, 0.05))), "erros_escrita": 0})
    return pd.DataFrame(linhas)


def test_concorrencia_resumo_testes_e_conclusao():
    conc = _concorrencia()
    resumo = robustez.resumo_concorrencia(conc)
    assert len(resumo) == 8 and resumo["escritor"].iloc[0] == "sim"
    testes = robustez.testes_concorrencia(conc).set_index("codigo")
    assert testes.loc["C-1", "rejeita_h0"] and testes.loc["C-2", "rejeita_h0"]
    assert testes.loc["C-2", "razao"] == pytest.approx(400 / 90, rel=0.1)
    texto = "\n".join(robustez.conclusoes(_dados(_durabilidade(), conc)))
    assert "C-1 confirmada" in texto and "C-2 confirmada" in texto
