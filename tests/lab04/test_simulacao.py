from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from labs.lab04_ci import simulacao


def test_gerar_amostra_reprodutivel_com_semente_fixa() -> None:
    amostra_1 = simulacao.gerar_amostra(30, 0.05, rng=42)
    amostra_2 = simulacao.gerar_amostra(30, 0.05, rng=42)
    assert np.array_equal(amostra_1, amostra_2)
    assert len(amostra_1) == 30
    assert set(np.unique(amostra_1)).issubset({0, 1})
    assert int(np.sum(amostra_1)) == 1

    amostra_efeito = simulacao.gerar_amostra(30, 5 / 30, rng=42)
    assert int(np.sum(amostra_efeito)) == 5

    amostra_outra_semente = simulacao.gerar_amostra(30, 0.05, rng=99)
    assert not np.array_equal(amostra_1, amostra_outra_semente)


def test_gerar_amostra_valida_argumentos() -> None:
    with pytest.raises(ValueError, match="Tamanho da amostra deve ser positivo"):
        simulacao.gerar_amostra(0, 0.05)
    with pytest.raises(ValueError, match="Tamanho da amostra deve ser positivo"):
        simulacao.gerar_amostra(-5, 0.05)
    with pytest.raises(ValueError, match=r"Probabilidade p deve estar no intervalo \[0, 1\]"):
        simulacao.gerar_amostra(30, -0.01)
    with pytest.raises(ValueError, match=r"Probabilidade p deve estar no intervalo \[0, 1\]"):
        simulacao.gerar_amostra(30, 1.05)


def test_gerar_matriz_amostras_e_contagens_binomiais() -> None:
    matriz = simulacao.gerar_matriz_amostras(100, 30, 0.05, rng=42)
    assert matriz.shape == (100, 30)
    assert set(np.unique(matriz)).issubset({0, 1})

    contagens = simulacao.gerar_contagens_binomiais(1000, 30, 0.05, rng=42)
    assert len(contagens) == 1000
    assert np.all(contagens >= 0) and np.all(contagens <= 30)
    assert abs(np.mean(contagens) - (30 * 0.05)) < 0.2


def test_aplicar_teste_z_calcula_estatistica_e_decisao() -> None:
    # Com n=30, p0=0.05 e k=1 (sem quebra de meta)
    res_sem_efeito = simulacao.aplicar_teste_z(1, 30, p0=0.05, alpha=0.05)
    assert res_sem_efeito.rejeita_h0 is False
    assert "Não rejeita H₀" in res_sem_efeito.decisao
    assert res_sem_efeito.p_valor > 0.05

    # Com n=30, p0=0.05 e k=5 (amostra observada no Ruff)
    res_com_efeito = simulacao.aplicar_teste_z(5, 30, p0=0.05, alpha=0.05)
    assert res_com_efeito.rejeita_h0 is True
    assert "Rejeita H₀" in res_com_efeito.decisao
    assert res_com_efeito.p_valor < 0.05
    assert res_com_efeito.estatistica == pytest.approx(2.932, abs=0.01)


def test_aplicar_teste_binomial_calcula_p_valor_exato_e_decisao() -> None:
    # Com n=30, p0=0.05 e k=1
    res_sem_efeito = simulacao.aplicar_teste_binomial(1, 30, p0=0.05, alpha=0.05)
    assert res_sem_efeito.rejeita_h0 is False
    assert res_sem_efeito.p_valor == pytest.approx(float(stats.binom.sf(0, 30, 0.05)))

    # Com n=30, p0=0.05 e k=5
    res_com_efeito = simulacao.aplicar_teste_binomial(5, 30, p0=0.05, alpha=0.05)
    assert res_com_efeito.rejeita_h0 is True
    assert res_com_efeito.p_valor == pytest.approx(float(stats.binom.sf(4, 30, 0.05)))
    assert res_com_efeito.p_valor == pytest.approx(0.0156, abs=0.0001)

    # Caso zero falhas
    res_zero = simulacao.aplicar_teste_binomial(0, 30, p0=0.05, alpha=0.05)
    assert res_zero.p_valor == 1.0
    assert res_zero.rejeita_h0 is False


def test_comparar_testes_ao_mesmo_conjunto() -> None:
    amostra = simulacao.gerar_amostra(30, 5 / 30, rng=42)
    comp = simulacao.comparar_testes(amostra, p0=0.05, alpha=0.05)
    assert comp.n == 30
    assert comp.falhas == 5
    assert comp.concordam is True
    assert comp.teste_z.rejeita_h0 is True
    assert comp.binomial.rejeita_h0 is True

    # Ponto de discordancia na fronteira: 4 falhas com n=30
    # Z rejeita (4 falhas -> z=2.094, p=0.018), mas Binomial nao rejeita (k=4 -> p=0.0608 > 0.05)
    comp_borda = simulacao.comparar_testes(4, n=30, p0=0.05, alpha=0.05)
    assert comp_borda.teste_z.rejeita_h0 is True
    assert comp_borda.binomial.rejeita_h0 is False
    assert comp_borda.concordam is False


def test_funcoes_vetorizadas_para_repeticoes_s02() -> None:
    contagens = np.array([0, 1, 3, 4, 5, 8])
    n = 30
    p0 = 0.05
    alpha = 0.05

    z_arr, p_z_arr, rej_z_arr = simulacao.simular_repeticoes_z(contagens, n, p0=p0, alpha=alpha)
    p_b_arr, rej_b_arr = simulacao.simular_repeticoes_binomial(contagens, n, p0=p0, alpha=alpha)

    for i, k in enumerate(contagens):
        indiv_z = simulacao.aplicar_teste_z(int(k), n, p0=p0, alpha=alpha)
        indiv_b = simulacao.aplicar_teste_binomial(int(k), n, p0=p0, alpha=alpha)

        assert z_arr[i] == pytest.approx(indiv_z.estatistica)
        assert p_z_arr[i] == pytest.approx(indiv_z.p_valor)
        assert rej_z_arr[i] == indiv_z.rejeita_h0

        assert p_b_arr[i] == pytest.approx(indiv_b.p_valor)
        assert rej_b_arr[i] == indiv_b.rejeita_h0
