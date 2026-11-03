"""Graficos interativos do dashboard do Lab04 (G1 e G2, issue #98).

Paleta validada (CVD e contraste) e fixa por papel, igual em todo o dashboard:
teste Z em azul, binomial exato em laranja, dados reais em cinza, simulados em verde-agua e violeta.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

from labs.lab04_ci import estatistica as est

COR_Z = "#2a78d6"
COR_BINOMIAL = "#eb6834"
COR_REAL = "#52514e"
COR_SIMULADO_H0 = "#1baf7a"
COR_SIMULADO_EFEITO = "#6250d6"
COR_H0_EXATA = "#898781"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
SUPERFICIE = "#fcfcfb"
FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def br(valor: float, casas: int = 3) -> str:
    """Numero com virgula decimal, como no restante do dashboard."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _transparente(cor: str, alfa: float) -> str:
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def _layout(fig: go.Figure, altura: int, legenda: dict | None = None, margem_topo: int = 110) -> go.Figure:
    fig.update_layout(
        height=altura, template="simple_white", font=dict(family=FONTE, size=13, color=TINTA_SECUNDARIA),
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, margin=dict(l=60, r=20, t=margem_topo, b=56),
        legend=legenda or dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                               font=dict(color=TINTA_SECUNDARIA)),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONTE, color=TINTA)),
        title=dict(font=dict(size=15, color=TINTA), x=0, xanchor="left", y=0.98, yanchor="top"),
    )
    fig.update_xaxes(showgrid=False, linecolor=EIXO, ticks="", title_font=dict(color=TINTA_SECUNDARIA))
    fig.update_yaxes(showgrid=True, gridcolor=GRADE, gridwidth=1, linecolor=EIXO, zeroline=False, ticks="",
                     title_font=dict(color=TINTA_SECUNDARIA))
    return fig


def g1_dados(amostra: est.Amostra, seed: int = est.SEED) -> go.Figure:
    """G1: execucoes reais ao lado de amostras simuladas do mesmo tamanho (sob H0 e com a taxa observada)."""
    sob_h0 = est.amostra_simulada(amostra.n, est.P0, seed)
    com_efeito = est.amostra_simulada(amostra.n, amostra.proporcao, seed)
    series = [
        ("Real (Ruff)", [amostra.sucessos, amostra.falhas], COR_REAL),
        (f"Simulado sob H0 (p = {br(est.P0, 2)})", [int((sob_h0 == 0).sum()), int(sob_h0.sum())], COR_SIMULADO_H0),
        (f"Simulado com a taxa real (p = {br(amostra.proporcao)})", [int((com_efeito == 0).sum()), int(com_efeito.sum())],
         COR_SIMULADO_EFEITO),
    ]
    fig = go.Figure()
    for nome, valores, cor in series:
        fig.add_bar(
            name=nome, x=["Sucesso (0)", "Falha (1)"], y=valores, marker=dict(color=cor, cornerradius=4),
            text=valores, textposition="outside", textfont=dict(color=TINTA_SECUNDARIA),
            hovertemplate=f"<b>{nome}</b><br>%{{x}}: %{{y}} de {amostra.n} execuções<extra></extra>",
        )
    fig.update_layout(barmode="group", bargap=0.55, bargroupgap=0.12,
                      title=f"G1 — Dados reais × simulados: {amostra.n} execuções do CI em main")
    fig.update_xaxes(title_text="Resultado da execução de CI")
    fig.update_yaxes(title_text=f"Execuções (de {amostra.n})", range=[0, amostra.n * 1.15])
    return _layout(fig, 430)


def g2_testes(amostra: est.Amostra, escala_log: bool = False) -> go.Figure:
    """G2: distribuicao de cada estatistica sob H0, regiao de rejeicao e p-valor da amostra real."""
    n, observado = amostra.n, amostra.falhas
    z_c, z_obs = est.z_critico(), est.estatistica_z(observado, n)
    p_z, p_b = est.p_valor_z(observado, n), est.p_valor_binomial(observado, n)
    k_c = est.falhas_criticas_binomial(n)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=(
        "Teste Z: z = (X − n·p₀) / √(n·p₀·(1−p₀)) comparado com N(0, 1)",
        f"Binomial exato: X ~ Binomial({n}; {br(est.P0, 2)})",
    ))

    # Teste Z: curva assumida, regiao de rejeicao, area do p-valor e a distribuicao real (discreta) de z sob H0.
    x = np.linspace(-3, 6.6, 800)  # cobre todos os valores possiveis de z exibidos (ate 9 falhas)
    pdf = stats.norm.pdf(x)
    fig.add_scatter(x=x, y=pdf, mode="lines", line=dict(color=COR_Z, width=2), name="Z: N(0, 1) assumida",
                    legendgroup="z", hovertemplate="z = %{x:.2f}<br>densidade = %{y:.4f}<extra></extra>", row=1, col=1)
    rejeita = x >= z_c
    fig.add_scatter(x=x[rejeita], y=pdf[rejeita], mode="lines", line=dict(width=0), fill="tozeroy",
                    fillcolor=_transparente(COR_Z, 0.15), name=f"Z: região de rejeição (z > {br(z_c)})",
                    legendgroup="z", hoverinfo="skip", row=1, col=1)
    area = x >= z_obs
    fig.add_scatter(x=x[area], y=pdf[area], mode="lines", line=dict(width=0), fill="tozeroy",
                    fillcolor=_transparente(COR_Z, 0.85), name=f"Z: p-valor da amostra = {br(p_z, 4)}",
                    legendgroup="z", hoverinfo="skip", row=1, col=1)
    k = np.arange(0, 10)
    massa = stats.binom.pmf(k, n, est.P0) * np.sqrt(n * est.P0 * (1 - est.P0))  # massa por unidade de z
    fig.add_scatter(x=(k - n * est.P0) / np.sqrt(n * est.P0 * (1 - est.P0)), y=massa, mode="markers",
                    marker=dict(color=COR_H0_EXATA, size=9, line=dict(color=SUPERFICIE, width=2)),
                    name="Z: valores possíveis de z sob H0 (X é discreto)", legendgroup="z",
                    customdata=np.stack([k, stats.binom.pmf(k, n, est.P0)], axis=1),
                    hovertemplate="%{customdata[0]} falhas → z = %{x:.2f}<br>P(X) = %{customdata[1]:.4f}<extra></extra>",
                    row=1, col=1)
    fig.add_vline(x=z_obs, line=dict(color=COR_Z, width=1, dash="dot"), row=1, col=1,
                  annotation_text=f"z observado = {br(z_obs, 2)}", annotation_position="top left",
                  annotation_font=dict(color=TINTA_SECUNDARIA, size=12))

    # Binomial exato: probabilidade de cada numero de falhas sob H0.
    falhas = np.arange(0, max(12, observado + 4))
    pmf = stats.binom.pmf(falhas, n, est.P0)
    cores = [COR_BINOMIAL if f >= k_c else _transparente(COR_BINOMIAL, 0.30) for f in falhas]
    fig.add_bar(x=falhas, y=pmf, marker=dict(color=cores, cornerradius=4), name=f"Binomial: região de rejeição (X ≥ {k_c})",
                legendgroup="b", hovertemplate="%{x} falhas<br>P(X = %{x}) = %{y:.4f}<extra></extra>", row=1, col=2)
    fig.add_bar(x=falhas[falhas >= observado], y=pmf[falhas >= observado],
                marker=dict(color="rgba(0,0,0,0)", line=dict(color=TINTA, width=1.5), pattern=dict(shape="/", fgcolor=TINTA)),
                name=f"Binomial: p-valor da amostra = P(X ≥ {observado}) = {br(p_b, 4)}", legendgroup="b",
                hovertemplate="%{x} falhas: entra no p-valor<br>P(X = %{x}) = %{y:.4f}<extra></extra>", row=1, col=2)
    fig.add_vline(x=k_c - 0.5, line=dict(color=COR_BINOMIAL, width=1, dash="dot"), row=1, col=2,
                  annotation_text=f"rejeita a partir de {k_c} falhas", annotation_position="top right",
                  annotation_font=dict(color=TINTA_SECUNDARIA, size=12))

    fig.update_layout(barmode="overlay", bargap=0.3, title="G2 — Distribuição de cada estatística sob H0")
    fig.update_xaxes(title_text="Estatística z (adimensional)", row=1, col=1)
    fig.update_xaxes(title_text=f"Número de falhas em {n} execuções", dtick=1, row=1, col=2)
    eixo_y = dict(type="log", exponentformat="power") if escala_log else {}
    fig.update_yaxes(title_text="Densidade sob H0", row=1, col=1, **eixo_y)
    fig.update_yaxes(title_text="Probabilidade sob H0", row=1, col=2, **eixo_y)
    if escala_log:
        fig.update_yaxes(range=[-6, 0], row=1, col=1)
        fig.update_yaxes(range=[-8, 0], row=1, col=2)
    for titulo in fig.layout.annotations[:2]:  # titulos dos paineis, acima da area de plotagem
        titulo.update(font=dict(size=13, color=TINTA), yshift=8)
    legenda = dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0, font=dict(color=TINTA_SECUNDARIA))
    return _layout(fig, 600, legenda=legenda, margem_topo=90)
