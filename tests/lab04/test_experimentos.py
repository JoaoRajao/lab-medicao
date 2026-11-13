from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from labs.lab04_ci import analise_real, estatistica, experimentos, simulacao


def test_q1_q2_q3_reprodutibilidade_e_contrato() -> None:
    primeiro = experimentos.gerar_resultados(42)
    segundo = experimentos.gerar_resultados(42)
    assert primeiro.equals(segundo)
    assert list(primeiro.columns) == list(experimentos.COLUNAS)
    assert len(primeiro) == 2 * len(experimentos.SITUACOES) * len(experimentos.P_GRADE)
    assert set(primeiro["teste"]) == {"Z", "Binomial"}
    assert set(primeiro["repeticoes"]) == {10_000}
    assert set(primeiro["seed"]) == {42}
    assert set(primeiro["situacao"]) == {"Base (n = 30)", "Amostra pequena (n = 10)"}
    assert set(primeiro["p_verdadeiro"]) == set(experimentos.P_GRADE)
    assert np.allclose(primeiro["taxa_rejeicao"], primeiro["rejeicoes"] / 10_000)


def test_ambos_testes_recebem_as_mesmas_contagens(monkeypatch: pytest.MonkeyPatch) -> None:
    capturas: dict[str, list[np.ndarray]] = {"Z": [], "Binomial": []}
    original_z = simulacao.simular_repeticoes_z
    original_binomial = simulacao.simular_repeticoes_binomial

    def z(falhas, n):
        capturas["Z"].append(falhas.copy())
        return original_z(falhas, n)

    def binomial(falhas, n):
        capturas["Binomial"].append(falhas.copy())
        return original_binomial(falhas, n)

    monkeypatch.setattr(simulacao, "simular_repeticoes_z", z)
    monkeypatch.setattr(simulacao, "simular_repeticoes_binomial", binomial)
    experimentos.gerar_resultados(42)
    assert len(capturas["Z"]) == len(experimentos.SITUACOES) * len(experimentos.P_GRADE)
    assert all(np.array_equal(z, b) for z, b in zip(capturas["Z"], capturas["Binomial"]))


def test_taxas_simuladas_conferem_com_probabilidades_exatas() -> None:
    for linha in experimentos.gerar_resultados(42).itertuples():
        critico = (estatistica.falhas_criticas_z(linha.n) if linha.teste == "Z"
                   else estatistica.falhas_criticas_binomial(linha.n))
        taxa_exata = float(stats.binom.sf(critico - 1, linha.n, linha.p_verdadeiro))
        erro_padrao = np.sqrt(taxa_exata * (1 - taxa_exata) / linha.repeticoes)
        assert abs(linha.taxa_rejeicao - taxa_exata) <= 3.29 * erro_padrao


def test_aplicacao_real_e_textos_vem_da_amostra() -> None:
    amostra = estatistica.carregar_amostra()
    tabela = analise_real.tabela(amostra)
    assert list(tabela["p-valor"]) == ["0,0017", "0,0156"]
    assert all("+11,67 p.p." in efeito for efeito in tabela["Tamanho do efeito"])
    assert all(decisao == "Rejeita H₀" for decisao in tabela["Conclusão (α = 0,05)"])
    texto = analise_real.texto_conclusao(amostra)
    assert "6,05%" in texto and "1,69%" in texto
    assert "87,66%" in texto and "74,75%" in texto
    assert "Amostra pequena (n = 10)" in texto
    assert "8,5% para Z" in texto and "1,2% para o binomial" in texto


def test_conclusao_incorpora_q3_quando_resultados_chegarem(tmp_path) -> None:
    resultados = experimentos.gerar_resultados(42)
    q3 = resultados[resultados["efeito"] == 0].copy()
    q3["situacao"] = "Amostra pequena (n = 10)"
    q3["n"] = 10
    q3.loc[q3["teste"] == "Z", "taxa_rejeicao"] = 0.11
    q3.loc[q3["teste"] == "Binomial", "taxa_rejeicao"] = 0.02
    caminho = tmp_path / "resultados.csv"
    pd.concat([resultados, q3]).to_csv(caminho, index=False)
    texto = analise_real.texto_conclusao(estatistica.carregar_amostra(), caminho)
    assert "Amostra pequena (n = 10)" in texto
    assert "11,0% para Z" in texto and "2,0% para o binomial" in texto


def test_conclusao_em_quatro_blocos_e_z_com_virgula() -> None:
    amostra = estatistica.carregar_amostra()
    assert analise_real.tabela(amostra)["Estatística"].iloc[0] == "z = 2,932"
    blocos = analise_real.blocos_conclusao(amostra)
    assert [titulo for titulo, _ in blocos] == ["Esperávamos × encontramos", "Recomendação", "Quando a escolha muda",
                                               "Situação adversa e limitação"]
    assert "binomial exato" in blocos[1][1] and "200 execuções" in blocos[2][1]
