"""Graficos do dashboard do Lab04 (G1 e G2, issue #98). Cada teste tem sempre a mesma cor."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from scipy import stats

from labs.lab04_ci import estatistica as est

COR_Z = "#2563eb"         # teste Z, em todos os graficos
COR_BINOMIAL = "#ea580c"  # binomial exato, em todos os graficos
COR_REAL = "#4b5563"
COR_SIMULADO_H0 = "#14b8a6"
COR_SIMULADO_EFEITO = "#a855f7"
COR_H0_EXATA = "#9ca3af"


def br(valor: float, casas: int = 3) -> str:
    """Numero com virgula decimal, como no restante do dashboard."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _eixos(fig: Figure, ncols: int):
    axes = fig.subplots(1, ncols)
    for ax in np.atleast_1d(axes):
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
    return axes


def g1_dados(amostra: est.Amostra, seed: int = est.SEED) -> Figure:
    """G1: execucoes reais ao lado de amostras simuladas do mesmo tamanho (sob H0 e com a taxa observada)."""
    sob_h0 = est.amostra_simulada(amostra.n, est.P0, seed)
    com_efeito = est.amostra_simulada(amostra.n, amostra.proporcao, seed)
    series = [
        ("Real (Ruff)", [amostra.sucessos, amostra.falhas], COR_REAL),
        (f"Simulado sob H0 (p = {br(est.P0, 2)})", [int((sob_h0 == 0).sum()), int(sob_h0.sum())], COR_SIMULADO_H0),
        (f"Simulado com p = {br(amostra.proporcao)} (taxa real)", [int((com_efeito == 0).sum()), int(com_efeito.sum())],
         COR_SIMULADO_EFEITO),
    ]
    fig = Figure(figsize=(8, 4.2), layout="constrained")
    ax = _eixos(fig, 1)
    largura = 0.26
    posicoes = np.arange(2)
    for i, (rotulo, valores, cor) in enumerate(series):
        barras = ax.bar(posicoes + (i - 1) * largura, valores, largura, label=rotulo, color=cor)
        ax.bar_label(barras, padding=2, fontsize=9)
    ax.set_xticks(posicoes, ["Sucesso (0)", "Falha (1)"])
    ax.set_xlabel("Resultado da execução de CI")
    ax.set_ylabel(f"Execuções (de {amostra.n})")
    ax.set_title(f"G1 — Dados reais × simulados: {amostra.n} execuções do CI em main")
    ax.legend(title="Amostra", fontsize=9)
    return fig


def g2_testes(amostra: est.Amostra) -> Figure:
    """G2: distribuicao de cada estatistica sob H0, regiao de rejeicao e p-valor da amostra real."""
    n, observado = amostra.n, amostra.falhas
    fig = Figure(figsize=(11, 4.4), layout="constrained")
    ax_z, ax_b = _eixos(fig, 2)

    # Teste Z: a curva normal que o teste assume e, em cinza, a distribuicao real de z sob H0 (discreta).
    z_c, z_obs = est.z_critico(), est.estatistica_z(observado, n)
    x = np.linspace(-3, max(4.5, z_obs + 1), 600)
    ax_z.plot(x, stats.norm.pdf(x), color=COR_Z, lw=2, label="N(0, 1) assumida pelo Z")
    regiao = x >= z_c
    ax_z.fill_between(x[regiao], stats.norm.pdf(x[regiao]), color=COR_Z, alpha=0.18,
                      label=f"Região de rejeição (z > {br(z_c)}, área 0,05)")
    area = x >= z_obs
    ax_z.fill_between(x[area], stats.norm.pdf(x[area]), color=COR_Z, alpha=0.75,
                      label=f"p-valor do exemplo = {br(est.p_valor_z(observado, n), 4)}")
    ax_z.axvline(z_obs, color=COR_Z, ls="--", lw=1)
    ax_z.annotate(f"z observado = {br(z_obs, 2)}\n({observado} falhas)", (z_obs, 0.2), xytext=(6, 0),
                  textcoords="offset points", fontsize=9)
    k = np.arange(0, 9)
    z_k = (k - n * est.P0) / np.sqrt(n * est.P0 * (1 - est.P0))
    escala = 1 / np.sqrt(n * est.P0 * (1 - est.P0))  # massa por unidade de z, comparavel a densidade
    ax_z.vlines(z_k, 0, stats.binom.pmf(k, n, est.P0) / escala, color=COR_H0_EXATA, lw=2, alpha=0.7,
                label="Distribuição real de z sob H0 (discreta)")
    zoom = ax_z.inset_axes([0.62, 0.42, 0.36, 0.33])
    cauda = x >= z_obs - 0.6
    zoom.plot(x[cauda], stats.norm.pdf(x[cauda]), color=COR_Z, lw=1.5)
    zoom.fill_between(x[cauda & regiao], stats.norm.pdf(x[cauda & regiao]), color=COR_Z, alpha=0.18)
    zoom.fill_between(x[area], stats.norm.pdf(x[area]), color=COR_Z, alpha=0.75)
    zoom.axvline(z_obs, color=COR_Z, ls="--", lw=1)
    zoom.set_title("zoom: área do p-valor", fontsize=8)
    zoom.tick_params(labelsize=7)
    ax_z.set_xlabel("Estatística z (adimensional)")
    ax_z.set_ylabel("Densidade sob H0")
    ax_z.set_title("Teste Z para uma proporção")
    ax_z.legend(fontsize=8, loc="upper left")

    # Binomial exato: probabilidade de cada numero de falhas sob H0.
    k_c = est.falhas_criticas_binomial(n)
    falhas = np.arange(0, max(11, observado + 3))
    pmf = stats.binom.pmf(falhas, n, est.P0)
    cores = [COR_BINOMIAL if f >= k_c else "#fed7aa" for f in falhas]
    ax_b.bar(falhas, pmf, color=cores, edgecolor=COR_BINOMIAL, linewidth=0.6)
    ax_b.bar(falhas[falhas >= observado], pmf[falhas >= observado], color="none", edgecolor="black",
             hatch="///", linewidth=0.8,
             label=f"p-valor do exemplo = P(X ≥ {observado}) = {br(est.p_valor_binomial(observado, n), 4)}")
    ax_b.axvline(k_c - 0.5, color=COR_BINOMIAL, ls="--", lw=1)
    ax_b.text(k_c - 0.4, pmf.max() * 0.9,
              f"Região de rejeição: X ≥ {k_c}\n(área real {br(est.erro_tipo_i_exato(k_c, n), 4)})",
              fontsize=9, color=COR_BINOMIAL)
    zoom_b = ax_b.inset_axes([0.55, 0.28, 0.42, 0.33])
    cauda_b = falhas >= k_c - 1
    zoom_b.bar(falhas[cauda_b], pmf[cauda_b], color=[c for c, f in zip(cores, falhas) if f >= k_c - 1],
               edgecolor=COR_BINOMIAL, linewidth=0.6)
    zoom_b.bar(falhas[falhas >= observado], pmf[falhas >= observado], color="none", edgecolor="black",
               hatch="///", linewidth=0.8)
    zoom_b.set_xticks(falhas[cauda_b])
    zoom_b.set_title("zoom: cauda e p-valor", fontsize=8)
    zoom_b.tick_params(labelsize=7)
    ax_b.set_xticks(falhas)
    ax_b.set_xlabel(f"Número de falhas em {n} execuções")
    ax_b.set_ylabel("Probabilidade sob H0")
    ax_b.set_title(f"Binomial exato: X ~ Binomial({n}; {br(est.P0, 2)})")
    ax_b.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.8))
    fig.suptitle("G2 — Distribuição da estatística sob H0, região de rejeição e p-valor da amostra real")
    return fig
