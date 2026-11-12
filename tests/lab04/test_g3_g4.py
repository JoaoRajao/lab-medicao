from __future__ import annotations

import re

import pandas as pd
import pytest

from labs.lab04_ci import estatistica as est
from labs.lab04_ci import graficos, resultados, roteiro, textos

AMOSTRA = est.Amostra(n=30, falhas=5, inicio="2026-10-30T22:03:25Z", fim="2026-11-02T18:14:10Z",
                      repositorio="astral-sh/ruff")


def resultados_ficticios() -> pd.DataFrame:
    """Resultados no formato do contrato, com rejeicoes = valor exato x 10.000 (so para testar o consumo)."""
    linhas = []
    for situacao, n in (("Base (n = 30)", 30), ("Amostra pequena (n = 10)", 10)):
        for p in resultados.P_GRADE:
            for teste in resultados.TESTES:
                rejeicoes = round(resultados.taxa_exata(teste, n, p) * 10_000)
                linhas.append({"situacao": situacao, "modelo": "bernoulli", "n": n, "p0": 0.05, "alpha": 0.05,
                               "p_verdadeiro": p, "efeito": p - 0.05, "teste": teste, "repeticoes": 10_000,
                               "rejeicoes": rejeicoes, "taxa_rejeicao": rejeicoes / 10_000, "seed": 42})
    return pd.DataFrame(linhas)


def frases(texto: str) -> int:
    return len(re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔ0-9])", texto.replace("**", "").strip()))


def test_exact_rejection_rates_match_the_known_type_i_errors_and_grow_with_the_effect():
    exatos = resultados.exatos()
    h0 = resultados.erro_tipo_i(exatos).set_index("teste")["taxa_exata"]
    assert h0["Z"] == pytest.approx(0.0608, abs=1e-4) and h0["Binomial"] == pytest.approx(0.0156, abs=1e-4)
    for _, curva in exatos.groupby("teste"):
        assert curva["taxa_exata"].is_monotonic_increasing
    assert resultados.taxa_exata("Binomial", 30, 0.05, alpha=0.01) < 0.01


def test_contract_rejects_inconsistent_results():
    df = resultados_ficticios()
    resultados.validar(df)
    with pytest.raises(ValueError, match="colunas"):
        resultados.validar(df.drop(columns="seed"))
    with pytest.raises(ValueError, match="taxa_rejeicao"):
        resultados.validar(df.assign(taxa_rejeicao=df["taxa_rejeicao"] + 0.01))
    with pytest.raises(ValueError, match="H0"):
        resultados.validar(df[df["efeito"] > 0])
    with pytest.raises(ValueError, match="teste"):
        resultados.validar(df.assign(teste="t"))


def test_results_round_trip_keeps_the_situation_order(tmp_path):
    assert resultados.carregar(tmp_path / "nao_existe.csv") is None
    caminho = resultados.salvar(resultados_ficticios(), tmp_path / "resultados.csv")
    lido = resultados.carregar(caminho)
    assert list(dict.fromkeys(lido["situacao"])) == ["Base (n = 30)", "Amostra pequena (n = 10)"]
    assert list(lido.columns) == list(resultados.COLUNAS)


@pytest.mark.parametrize("com_simulacao", [True, False])
def test_g3_and_g4_have_titles_axes_legend_reference_lines_and_fixed_colors(com_simulacao):
    simulados = resultados_ficticios() if com_simulacao else None
    exatos = resultados.exatos(simulados)
    g3 = graficos.g3_erro_tipo_i(simulados, exatos)
    assert g3.layout.title.text.startswith("G3") and g3.layout.xaxis.title.text and g3.layout.yaxis.title.text
    assert [t.marker.color for t in g3.data if t.type == "bar"] == [graficos.COR_Z, graficos.COR_BINOMIAL]
    assert any(s.y0 == 5 for s in g3.layout.shapes)  # linha em 5%
    assert any(t.name == "Valor exato (binomial)" for t in g3.data) is com_simulacao

    g4 = graficos.g4_poder(simulados, exatos, AMOSTRA.proporcao - est.P0)
    assert g4.layout.title.text.startswith("G4") and g4.layout.xaxis.title.text and g4.layout.yaxis.title.text
    assert {t.line.color for t in g4.data} == {graficos.COR_Z, graficos.COR_BINOMIAL}
    assert len(g4.data) == 2 * len(set(exatos["situacao"]))
    assert all(t.name for t in g4.data)


def test_g3_g4_texts_come_from_the_data_and_keep_two_to_four_sentences():
    simulados = resultados_ficticios()
    exatos = resultados.exatos(simulados)
    t3, t4 = textos.g3(simulados, exatos), textos.g4(simulados, exatos, AMOSTRA.proporcao - est.P0)
    assert 2 <= frases(t3) <= 4 and 2 <= frases(t4) <= 4
    assert "**liberal**" in t3 and "**conservador**" in t3 and "6,1%" in t3
    assert "10.000 conjuntos" in t4 and "Amostra pequena" in t4
    assert "valores exatos" in textos.g3(None, resultados.exatos())


def test_presentation_script_answers_all_questions_with_at_least_four_per_member():
    simulados = resultados_ficticios()
    respostas = roteiro.respostas(AMOSTRA, simulados, resultados.exatos(simulados))
    assert sorted(respostas) == list(range(1, 16)) and all(respostas.values())
    contagem = pd.Series(roteiro.RESPONSAVEL).value_counts()
    assert set(contagem.index) == {"Pedro", "João", "Salomão"} and contagem.min() >= 4
    assert "0,0156" in respostas[7] and "**binomial exato**" in respostas[15]
    assert "Amostra pequena (n = 10)" in respostas[11]
    assert "Pendente" in roteiro.respostas(AMOSTRA, None, resultados.exatos())[11]
    texto = roteiro.markdown(AMOSTRA, simulados, resultados.exatos(simulados))
    assert all(pergunta in texto for pergunta, _ in roteiro.PERGUNTAS.values())


def test_single_command_validation_checks_charts_and_section_order():
    from labs.lab04_ci import executar

    problemas = executar.validar()
    assert not any("sem título" in p or "exceção" in p or "fora da ordem" in p for p in problemas)


def test_sample_size_discussion_uses_exact_power():
    p = AMOSTRA.proporcao
    n_80 = {teste: resultados.n_para_poder(teste, p) for teste in resultados.TESTES}
    assert n_80 == {"Z": 39, "Binomial": 46}
    assert all(resultados.taxa_exata(t, n, p) >= 0.8 for t, n0 in n_80.items() for n in range(n0, 120))
    assert resultados.taxa_exata("Binomial", n_80["Binomial"] - 1, p) < 0.8 or resultados.taxa_exata(
        "Binomial", n_80["Binomial"] - 2, p) < 0.8
    fig = graficos.poder_por_n(resultados.poder_por_n(p), p, AMOSTRA.n, n_80)
    assert fig.layout.title.text and fig.layout.xaxis.title.text and fig.layout.yaxis.title.text
    assert [t.line.color for t in fig.data[:2]] == [graficos.COR_Z, graficos.COR_BINOMIAL]
    texto = textos.tamanho_amostra(AMOSTRA, n_80)
    assert 2 <= frases(texto) <= 4 and "76,0%" in texto and "57,6%" in texto and "39 execuções" in texto
