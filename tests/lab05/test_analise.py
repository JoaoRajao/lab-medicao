"""Testes da analise estatistica e das visualizacoes do Lab05 (issue #122)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from labs.lab05_sqlite import analise, graficos


def test_estatistica_descritiva_cobre_todas_combinacoes_e_durabilidade() -> None:
    df = analise.carregar_dados()
    desc = analise.estatistica_descritiva(df)

    assert len(desc) == 12 * len(analise.METRICAS)
    assert set(desc["n"]) == {30}
    assert (desc["iqr"] >= 0.0).all()
    assert (desc["cv"] >= 0.0).all()
    dur_wal_normal = desc.loc[desc["configuracao"] == "WAL/NORMAL", "durabilidade_m6"].unique()
    assert list(dur_wal_normal) == ["Nao duravel apos queda de energia"]


def test_detectar_atipicos_regra_3_iqr() -> None:
    base = pd.DataFrame({
        "bloco": [1, 2, 3, 4, 5, 6],
        "ordem": [1, 1, 1, 1, 1, 1],
        "carga": ["escrita"] * 6,
        "journal_mode": ["WAL"] * 6,
        "synchronous": ["FULL"] * 6,
        "ops_por_s": [100.0, 102.0, 101.0, 99.0, 100.5, 500.0],
        "latencia_mediana_ms": [10.0, 9.8, 9.9, 10.1, 10.0, 2.0],
        "latencia_p95_ms": [12.0, 11.8, 11.9, 12.1, 12.0, 3.0],
    })
    atipicos = analise.detectar_atipicos(base, metricas=("ops_por_s",))
    assert len(atipicos) == 1
    assert atipicos.iloc[0]["bloco"] == 6
    assert atipicos.iloc[0]["valor"] == pytest.approx(500.0)


def test_coleta_completa_sem_atipicos_em_vazao() -> None:
    df = analise.carregar_dados()
    atipicos_vazao = analise.detectar_atipicos(df, metricas=("ops_por_s",))
    assert atipicos_vazao.empty


def test_razao_medianas_bootstrap_e_rank_bisserial() -> None:
    a = np.array([20.0, 22.0, 24.0, 26.0, 28.0])
    b = np.array([10.0, 11.0, 12.0, 13.0, 14.0])

    razao, ic_inf, ic_sup = analise.razao_medianas_bootstrap(a, b, reps=500, seed=42)
    assert razao == pytest.approx(2.0)
    assert ic_inf <= razao <= ic_sup
    assert analise.rank_bisserial_pareado(a, b) == pytest.approx(1.0)
    assert analise.rank_bisserial_pareado(b, a) == pytest.approx(-1.0)
    assert analise.rank_bisserial_pareado(a, a) == pytest.approx(0.0)

    with pytest.raises(ValueError):
        analise.razao_medianas_bootstrap(a, np.array([0.0, 0.0, 0.0, 0.0, 0.0]))


def test_correcao_holm() -> None:
    ajustados = analise.correcao_holm([0.01, 0.04, 0.03])
    np.testing.assert_allclose(ajustados, [0.03, 0.06, 0.06])


def test_testes_hipoteses_e_simulacao_poder() -> None:
    df = analise.carregar_dados()
    piloto = analise.carregar_dados(analise.RAW_PILOTO)

    testes = analise.executar_testes_hipoteses(df)
    conf = testes[testes["confirmatoria"]].set_index("codigo")
    assert list(conf.index) == ["H-1", "H-2", "H-3"]
    assert bool(conf["rejeita_h0"].all())
    assert bool(conf["sensibilidade_t_coincide"].all())
    assert (conf["p_holm"] < analise.ALPHA).all()

    exp1 = testes.loc[testes["codigo"] == "Exp-1"].iloc[0]
    assert not bool(exp1["rejeita_h0"])
    assert 0.95 < exp1["razao_medianas"] < 1.02

    poder = analise.simular_poder_piloto(piloto, reps=500)
    assert len(poder) == 3
    assert (poder["poder_simulado"] > 0.95).all()
    assert (poder["erro_tipo_i_simulado"] < 0.10).all()


def test_pipeline_completo_e_graficos(tmp_path) -> None:
    saida_proc = tmp_path / "processed"
    saida_fig = tmp_path / "figuras"
    resultados = analise.executar_analise(saida_dir=saida_proc)
    df = analise.carregar_dados()
    caminhos = graficos.gerar_todos_graficos(df, resultados["descritiva"], resultados["testes"], saida_fig)

    for nome in ("descritiva.csv", "atipicos.csv", "testes_hipoteses.csv", "simulacao_poder.csv", "resumo.json"):
        assert (saida_proc / nome).exists()
    assert len(caminhos) == 4
    assert all(c.exists() and c.stat().st_size > 0 for c in caminhos)
