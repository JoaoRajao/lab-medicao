from __future__ import annotations

import math
from pathlib import Path

import pytest
from scipy import stats
from streamlit.testing.v1 import AppTest

from labs.lab04_ci import estatistica as est
from labs.lab04_ci import graficos, textos

APP = Path(__file__).resolve().parents[2] / "labs" / "lab04_ci" / "app.py"
AMOSTRA = est.Amostra(n=30, falhas=5, inicio="2026-10-30T22:03:25Z", fim="2026-11-02T18:14:10Z",
                      repositorio="astral-sh/ruff")


def test_real_sample_is_read_from_the_versioned_csv():
    amostra = est.carregar_amostra()
    assert (amostra.n, amostra.falhas, amostra.repositorio) == (30, 5, "astral-sh/ruff")


def test_statistics_match_scipy_for_the_real_sample():
    assert est.estatistica_z(5, 30) == pytest.approx((5 - 1.5) / math.sqrt(30 * 0.05 * 0.95))
    assert est.p_valor_z(5, 30) == pytest.approx(stats.norm.sf(est.estatistica_z(5, 30)))
    assert est.p_valor_binomial(5, 30) == pytest.approx(stats.binomtest(5, 30, 0.05, alternative="greater").pvalue)


def test_rejection_regions_and_their_real_type_i_error():
    assert est.z_critico() == pytest.approx(1.6449, abs=1e-4)
    assert est.falhas_criticas_z(30) == 4      # z(3) = 1,26; z(4) = 2,09
    assert est.falhas_criticas_binomial(30) == 5  # P(X >= 4) = 0,061 > 0,05
    assert est.erro_tipo_i_exato(4, 30) > 0.05 > est.erro_tipo_i_exato(5, 30)


def test_simulated_sample_is_reproducible_and_binary():
    first = est.amostra_simulada(30, 0.2)
    assert (first == est.amostra_simulada(30, 0.2)).all()
    assert set(first.tolist()) <= {0, 1} and len(first) == 30


def test_figures_have_titles_axis_labels_legends_and_fixed_test_colors():
    g1 = graficos.g1_dados(AMOSTRA)
    assert g1.layout.title.text.startswith("G1")
    assert g1.layout.xaxis.title.text and g1.layout.yaxis.title.text
    assert [trace.marker.color for trace in g1.data] == [graficos.COR_REAL, graficos.COR_SIMULADO_H0,
                                                          graficos.COR_SIMULADO_EFEITO]
    assert all(trace.text is not None for trace in g1.data)  # rotulos de valor: alivio de contraste

    g2 = graficos.g2_testes(AMOSTRA)
    assert g2.layout.title.text.startswith("G2")
    assert g2.layout.xaxis.title.text.startswith("Estatística z") and g2.layout.xaxis2.title.text.startswith("Número")
    nomes = [trace.name for trace in g2.data]
    assert any(nome.startswith("Z: p-valor") for nome in nomes) and any(nome.startswith("Binomial: p-valor") for nome in nomes)
    assert g2.data[0].line.color == graficos.COR_Z
    assert graficos.COR_BINOMIAL in g2.data[4].marker.color  # barras da regiao de rejeicao
    assert all(trace.showlegend is not False for trace in g2.data)


def test_log_scale_switches_both_vertical_axes():
    g2 = graficos.g2_testes(AMOSTRA, escala_log=True)
    assert g2.layout.yaxis.type == "log" and g2.layout.yaxis2.type == "log"
    assert graficos.g2_testes(AMOSTRA).layout.yaxis.type != "log"


def test_texts_come_from_the_data_and_keep_two_to_four_sentences():
    for texto in (textos.g1(AMOSTRA), textos.g2(AMOSTRA)):
        frases = [f for f in texto.replace("**", "").split(". ") if f.strip()]
        assert 2 <= len(frases) <= 4
    assert "0,0156" in textos.g2(AMOSTRA) and "6,1%" in textos.g2(AMOSTRA)
    assert "30 execuções" in textos.fonte(AMOSTRA) and "unicaudais à direita" in textos.desenho()
    assert "5%" in textos.pergunta(AMOSTRA) and [h for h, _ in textos.hipoteses()] == ["H₀", "H₁"]
    linhas = textos.comparacao(AMOSTRA)
    assert [l["Rejeita H₀ a partir de"] for l in linhas] == ["4 falhas", "5 falhas"]
    assert [l["Erro tipo I real"] for l in linhas] == ["6,1%", "1,6%"]


def test_dashboard_runs_and_shows_the_s01_sections_in_order():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    headers = [h.value for h in app.header]
    assert headers == ["1. Cenário", "2. Os dados", "3. Como os testes funcionam"]
    assert any("github.com/JoaoRajao/lab-medicao" in m.value for m in app.markdown)
    assert any("projects/4" in m.value for m in app.markdown)
    assert [m.label for m in app.metric][:2] == ["Execuções observadas", "Falhas"]
    assert len(app.toggle) == 1
