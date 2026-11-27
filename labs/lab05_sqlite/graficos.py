"""Visualizacoes do Lab05: vazao em escala logaritmica, interacao, leitura e tamanhos de efeito (issue #122).

Gera os graficos em ``labs/lab05_sqlite/figuras/`` a partir dos dados versionados
e das tabelas produzidas por ``labs.lab05_sqlite.analise``.

    python -m labs.lab05_sqlite.graficos
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from labs.lab05_sqlite import analise

FIGURAS_DIR = analise.BASE_DIR / "figuras"

ORDEM_CONFIGS = ("DELETE/FULL", "DELETE/NORMAL", "WAL/FULL", "WAL/NORMAL")
CORES_CONFIG = {
    "DELETE/FULL": "#3b82f6",
    "DELETE/NORMAL": "#60a5fa",
    "WAL/FULL": "#10b981",
    "WAL/NORMAL": "#f59e0b",
}
ROTULOS_CARGA = {
    "escrita": "Escrita (500 INSERTs, 1/transação)",
    "leitura": "Leitura avulsa (5.000 SELECTs, autocommit)",
    "leitura_transacao": "Leitura em transação única (5.000 SELECTs)",
}


def _configurar_estilo() -> None:
    plt.rcParams.update({
        "figure.dpi": 150,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
    })


def grafico_vazao_log(df: pd.DataFrame, destino: Path) -> Path:
    """Boxplot com pontos individuais de vazao (ops/s) em escala logaritmica."""
    _configurar_estilo()
    dados = df.copy()
    dados["configuracao"] = dados["journal_mode"] + "/" + dados["synchronous"]

    cargas = ("escrita", "leitura", "leitura_transacao")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True)
    rng = np.random.default_rng(analise.SEED)

    for ax, carga in zip(axes, cargas):
        sub = dados[dados["carga"] == carga]
        series = [sub.loc[sub["configuracao"] == cfg, "ops_por_s"].to_numpy() for cfg in ORDEM_CONFIGS]
        bp = ax.boxplot(series, tick_labels=ORDEM_CONFIGS, patch_artist=True, showfliers=False, widths=0.5)
        for patch, cfg in zip(bp["boxes"], ORDEM_CONFIGS):
            patch.set_facecolor(CORES_CONFIG[cfg])
            patch.set_alpha(0.35)
        for mediana in bp["medians"]:
            mediana.set_color("#111827")
            mediana.set_linewidth(1.8)

        for idx, (vals, cfg) in enumerate(zip(series, ORDEM_CONFIGS), start=1):
            jitter = rng.uniform(-0.14, 0.14, size=len(vals))
            ax.scatter(np.full(len(vals), idx) + jitter, vals, s=14, alpha=0.7,
                       color=CORES_CONFIG[cfg], edgecolors="none")

        ax.set_yscale("log")
        ax.set_title(ROTULOS_CARGA[carga], fontsize=10.5, pad=8)
        ax.tick_params(axis="x", rotation=25)
        ax.set_xlabel("Configuração (journal / synchronous)")

    axes[0].set_ylabel("Vazão (operações/s, escala log)")
    legenda = [
        plt.Line2D([0], [0], color=CORES_CONFIG[c], lw=6, alpha=0.6,
                   label=f"{c} ({'não durável' if c == 'WAL/NORMAL' else 'durável'})")
        for c in ORDEM_CONFIGS
    ]
    fig.legend(handles=legenda, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Desempenho do SQLite por configuração e carga (n = 30 blocos)", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))

    caminho = destino / "vazao_por_configuracao_log.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
    return caminho


def grafico_interacao(descritiva: pd.DataFrame, destino: Path) -> Path:
    """Grafico de interacao journal_mode x synchronous para mediana e IQR da vazao."""
    _configurar_estilo()
    sub = descritiva[descritiva["metrica"] == "ops_por_s"]
    cargas = ("escrita", "leitura", "leitura_transacao")
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8), sharey=True)
    x = np.array([0, 1])

    for ax, carga in zip(axes, cargas):
        sc = sub[sub["carga"] == carga]
        for journal, cor, marcador in (("DELETE", "#3b82f6", "o"), ("WAL", "#10b981", "s")):
            sj = sc[sc["journal_mode"] == journal].set_index("synchronous").loc[["FULL", "NORMAL"]]
            med = sj["mediana"].to_numpy()
            yerr = np.vstack([med - sj["q1"].to_numpy(), sj["q3"].to_numpy() - med])
            ax.errorbar(x, med, yerr=yerr, marker=marcador, linewidth=2.2, markersize=7,
                        capsize=4, color=cor, label=f"journal_mode = {journal}")

        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(["FULL\n(durável)", "NORMAL\n(não durável no WAL)"])
        ax.set_xlabel("Modo synchronous")
        ax.set_title(ROTULOS_CARGA[carga], fontsize=10.5)

    axes[0].set_ylabel("Mediana da vazão ± IQR (operações/s, escala log)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Interação journal_mode × synchronous (mediana e IQR em 30 blocos)", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))

    caminho = destino / "interacao_journal_synchronous.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
    return caminho


def grafico_comparacao_leituras(descritiva: pd.DataFrame, destino: Path) -> Path:
    """Compara leitura avulsa (autocommit) vs transacao unica (synchronous=FULL)."""
    _configurar_estilo()
    sub = descritiva[
        (descritiva["metrica"] == "ops_por_s")
        & (descritiva["synchronous"] == "FULL")
        & (descritiva["carga"].isin(["leitura", "leitura_transacao"]))
    ]
    cargas = ("leitura", "leitura_transacao")
    rotulos = ("Leitura avulsa\n(autocommit)", "Leitura em\ntransação única")
    x = np.arange(len(cargas))
    largura = 0.34

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for desloc, journal, cor in ((-largura / 2, "DELETE", "#3b82f6"), (largura / 2, "WAL", "#10b981")):
        sj = sub[sub["journal_mode"] == journal].set_index("carga").loc[list(cargas)]
        med = sj["mediana"].to_numpy()
        barras = ax.bar(x + desloc, med, width=largura, color=cor, alpha=0.85, label=f"journal_mode = {journal}")
        for barra, val in zip(barras, med):
            ax.text(barra.get_x() + barra.get_width() / 2, val * 1.02,
                    f"{val:,.0f}".replace(",", "."), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(rotulos)
    ax.set_ylabel("Vazão mediana (consultas/s)")
    ax.set_ylim(0, sub["mediana"].max() * 1.18)
    ax.set_title("Validade de construto na leitura (synchronous = FULL): autocommit vs transação única",
                 fontsize=11.5, fontweight="bold", pad=10)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()

    caminho = destino / "leitura_autocommit_vs_transacao.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
    return caminho


def grafico_tamanho_efeito(testes: pd.DataFrame, destino: Path) -> Path:
    """Grafico de razao das medianas com IC 95% (bootstrap) para cada comparacao."""
    _configurar_estilo()
    df_plot = testes.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(df_plot))

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for i, row in df_plot.iterrows():
        cor = "#10b981" if row["confirmatoria"] else "#64748b"
        marcador = "o" if row["rejeita_h0"] else "s"
        razao = row["razao_medianas"]
        xerr = [[razao - row["ic95_razao_inf"]], [row["ic95_razao_sup"] - razao]]
        ax.errorbar(razao, i, xerr=xerr, fmt=marcador, color=cor, ecolor=cor,
                    capsize=4, markersize=7, linewidth=2)
        ax.text(razao, i + 0.18, f"{razao:.2f}×", ha="center", va="bottom", fontsize=9, color="#111827")

    ax.axvline(1.0, color="#ef4444", linestyle="--", linewidth=1.2, label="Sem efeito (razão = 1,0)")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['codigo']}: {r['descricao']}" for _, r in df_plot.iterrows()], fontsize=9.5)
    ax.set_xlabel("Razão das medianas de vazão (escala log, IC 95% por bootstrap)")
    ax.set_title("Tamanho do efeito nas comparações planejadas (H-1 a H-3) e exploratórias",
                 fontsize=12, fontweight="bold", pad=10)

    legenda = [
        plt.Line2D([0], [0], marker="o", color="#10b981", lw=0, markersize=7, label="Confirmatória (p_Holm < 0,05)"),
        plt.Line2D([0], [0], marker="s", color="#64748b", lw=0, markersize=7, label="Exploratória"),
        plt.Line2D([0], [0], color="#ef4444", linestyle="--", lw=1.2, label="Sem efeito (1,0×)"),
    ]
    ax.legend(handles=legenda, loc="lower right", frameon=False)
    fig.tight_layout()

    caminho = destino / "tamanho_efeito_razoes.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
    return caminho


def gerar_todos_graficos(
    df: pd.DataFrame,
    descritiva: pd.DataFrame,
    testes: pd.DataFrame,
    destino: Path = FIGURAS_DIR,
) -> list[Path]:
    """Gera todas as figuras do Lab05 e retorna os caminhos salvos."""
    destino.mkdir(parents=True, exist_ok=True)
    return [
        grafico_vazao_log(df, destino),
        grafico_interacao(descritiva, destino),
        grafico_comparacao_leituras(descritiva, destino),
        grafico_tamanho_efeito(testes, destino),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerador de graficos do Lab05")
    parser.add_argument("--destino", type=Path, default=FIGURAS_DIR)
    args = parser.parse_args()

    resultados = analise.executar_analise()
    df = analise.carregar_dados()
    caminhos = gerar_todos_graficos(df, resultados["descritiva"], resultados["testes"], args.destino)
    for c in caminhos:
        print(f"Grafico salvo em {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
