from __future__ import annotations

import math
from pathlib import Path

import pytest
from matplotlib.figure import Figure
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
    g2 = graficos.g2_testes(AMOSTRA)
    assert isinstance(g1, Figure) and isinstance(g2, Figure)
    ax_g1 = g1.axes[0]
    assert ax_g1.get_title().startswith("G1") and ax_g1.get_xlabel() and ax_g1.get_ylabel() and ax_g1.get_legend()
    ax_z, ax_b = [ax for ax in g2.axes if ax.get_xlabel()][:2]
    assert "Z" in ax_z.get_title() and "Binomial" in ax_b.get_title()
    assert ax_z.get_legend() and ax_b.get_legend()
    assert ax_z.lines[0].get_color() == graficos.COR_Z
    assert any(patch.get_facecolor()[:3] == pytest.approx((0.918, 0.345, 0.047), abs=0.01) for patch in ax_b.patches)


def test_texts_come_from_the_data_and_keep_two_to_four_sentences():
    for texto in (textos.g1(AMOSTRA), textos.g2(AMOSTRA)):
        frases = [f for f in texto.replace("**", "").split(". ") if f.strip()]
        assert 2 <= len(frases) <= 4
    assert "0,0156" in textos.g2(AMOSTRA) and "6,1%" in textos.g2(AMOSTRA)
    assert "5 falhas" in textos.cenario(AMOSTRA) and "unicaudais à direita" in textos.cenario(AMOSTRA)


def test_dashboard_runs_and_shows_the_s01_sections_in_order():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    headers = [h.value for h in app.header]
    assert headers == ["1. Cenário", "2. Os dados", "3. Como os testes funcionam"]
    assert "github.com/JoaoRajao/lab-medicao" in app.markdown[0].value
