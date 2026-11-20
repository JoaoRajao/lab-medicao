from __future__ import annotations

import csv
import json
import sqlite3

import pytest

from labs.lab05_sqlite import coleta

PEQUENO = coleta.Parametros(repeticoes=2, escritas=5, linhas_leitura=50, leituras=10)


def test_configuracao_e_aplicada_e_conferida(tmp_path):
    con = coleta.conectar(tmp_path / "x.db", "WAL", "NORMAL")
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert con.execute("PRAGMA synchronous").fetchone()[0] == 1
    con.close()


def test_cada_bloco_mede_todas_as_configuracoes_em_ordem_aleatoria_reprodutivel(tmp_path):
    linhas = coleta.coletar(PEQUENO, tmp_path, progresso=lambda _: None)
    assert len(linhas) == PEQUENO.repeticoes * len(coleta.CARGAS) * len(coleta.CONFIGURACOES)
    for bloco in (1, 2):
        do_bloco = [(l["carga"], l["journal_mode"], l["synchronous"]) for l in linhas if l["bloco"] == bloco]
        assert sorted(do_bloco) == sorted((c, j, s) for c in coleta.CARGAS for j, s in coleta.CONFIGURACOES)
    ordem = lambda ls: [(l["bloco"], l["carga"], l["journal_mode"], l["synchronous"]) for l in ls]
    assert ordem(linhas) == ordem(coleta.coletar(PEQUENO, tmp_path, progresso=lambda _: None))
    assert all(l["operacoes"] == (5 if l["carga"] == "escrita" else 10) and l["ops_por_s"] > 0 for l in linhas)
    assert {l["carga"] for l in linhas} == {"escrita", "leitura", "leitura_transacao"}
    assert {l["sqlite_version"] for l in linhas} == {sqlite3.sqlite_version}
    assert not list(tmp_path.iterdir())  # bancos temporarios removidos


def test_salva_csv_no_contrato_e_ambiente(tmp_path):
    linhas = coleta.coletar(PEQUENO, tmp_path, progresso=lambda _: None)
    caminho = coleta.salvar(linhas, coleta.ambiente(PEQUENO), "teste", tmp_path / "raw")
    with caminho.open(encoding="utf-8") as f:
        lidas = list(csv.DictReader(f))
    assert tuple(lidas[0]) == coleta.COLUNAS and len(lidas) == len(linhas)
    info = json.loads((tmp_path / "raw" / "teste_ambiente.json").read_text(encoding="utf-8"))
    assert info["sqlite_version"] == sqlite3.sqlite_version and info["parametros"]["seed"] == 42


def test_configuracao_invalida_e_recusada(tmp_path):
    with pytest.raises(ValueError, match="fora do experimento"):
        coleta.conectar(tmp_path / "y.db", "WAL", "QUALQUER")
    with pytest.raises(ValueError):
        coleta.conectar(tmp_path / "y.db", "MEMORY", "FULL")
