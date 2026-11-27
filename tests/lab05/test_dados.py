"""Validacao das coletas completas versionadas: Windows (#121) e replicacoes (#137: WSL2 e GitHub Actions). Cada CSV segue o
desenho planejado na proposta."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from labs.lab05_sqlite import coleta

RAW = Path(coleta.__file__).parent / "data" / "raw"


COLETAS = ("coleta_completa", "coleta_linux", "coleta_actions_Linux", "coleta_actions_Windows",
           "coleta_actions_macOS")


@pytest.fixture(scope="module", params=COLETAS)
def coleta_versionada(request) -> tuple[pd.DataFrame, dict]:
    nome = request.param
    return (pd.read_csv(RAW / f"{nome}.csv"),
            json.loads((RAW / f"{nome}_ambiente.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def dados(coleta_versionada) -> pd.DataFrame:
    return coleta_versionada[0]


@pytest.fixture(scope="module")
def ambiente(coleta_versionada) -> dict:
    return coleta_versionada[1]


def test_colunas_e_sem_valores_faltando(dados):
    assert list(dados.columns) == list(coleta.COLUNAS)
    assert not dados.isna().any().any()


def test_blocos_completos_com_ordem_sorteada(dados, ambiente):
    blocos = ambiente["parametros"]["repeticoes"]
    combinacoes = len(coleta.CARGAS) * len(coleta.CONFIGURACOES)
    assert len(dados) == blocos * combinacoes
    assert sorted(dados["bloco"].unique()) == list(range(1, blocos + 1))
    for _, bloco in dados.groupby("bloco"):
        assert sorted(bloco["ordem"]) == list(range(1, combinacoes + 1))
        assert not bloco.duplicated(["carga", "journal_mode", "synchronous"]).any()
    # a ordem foi sorteada: nem todos os blocos repetem a mesma sequencia
    sequencias = dados.sort_values(["bloco", "ordem"]).groupby("bloco")["carga"].apply(tuple)
    assert sequencias.nunique() > 1


def test_tratamentos_e_cargas_sao_os_do_experimento(dados):
    assert set(dados["carga"]) == set(coleta.CARGAS)
    assert set(zip(dados["journal_mode"], dados["synchronous"])) == set(coleta.CONFIGURACOES)


def test_valores_coerentes_com_os_parametros(dados, ambiente):
    p = ambiente["parametros"]
    assert (dados.loc[dados["carga"] == "escrita", "operacoes"] == p["escritas"]).all()
    assert (dados.loc[dados["carga"] != "escrita", "operacoes"] == p["leituras"]).all()
    assert (dados[["duracao_s", "ops_por_s", "latencia_mediana_ms", "latencia_p95_ms"]] > 0).all().all()
    assert (dados["latencia_mediana_ms"] <= dados["latencia_p95_ms"]).all()
    vazao = dados["operacoes"] / dados["duracao_s"]
    assert (abs(vazao / dados["ops_por_s"] - 1) < 0.01).all()


def test_rastreabilidade_com_o_ambiente(dados, ambiente):
    assert set(dados["sqlite_version"]) == {ambiente["sqlite_version"]}
    assert set(dados["seed"]) == {ambiente["parametros"]["seed"]}
    assert ambiente["discos"], "o modelo do disco precisa estar registrado"
