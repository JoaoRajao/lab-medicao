from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BAR = "#2a78d6"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_INK = "#0b0b0b"
COLOR_MUTED = "#898781"
SURFACE = "#fcfcfb"


def fetch_distribution(
    conn: duckdb.DuckDBPyConnection, source: str, buckets: list[tuple[str, str]]
) -> list[tuple[str, int]]:
    """Conta linhas de `source` (tabela ou view ja registrada na conexao) por faixa.

    `buckets` e uma lista de (rotulo, condicao_sql). Generico: nao sabe nada
    sobre o tema/lab, so monta um UNION ALL de contagens.
    """
    selects = [
        f"select '{label}' as faixa, count(*) as total, {index} as ord "
        f"from {source} where {condition}"
        for index, (label, condition) in enumerate(buckets)
    ]
    query = " union all ".join(selects) + " order by ord"
    rows = conn.execute(query).fetchall()
    return [(label, total) for label, total, _ in rows]


def plot_distribution(rows: list[tuple[str, int]], title: str, xlabel: str, output_path: Path) -> None:
    """Grafico de barras horizontais para uma lista de (rotulo, contagem)."""
    labels = [row[0] for row in rows]
    counts = [row[1] for row in rows]
    total = sum(counts)
    max_count = max(counts)

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    y_pos = range(len(labels))
    bars = ax.barh(y_pos, counts, height=0.6, color=COLOR_BAR, zorder=3)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, color=COLOR_INK, fontsize=10)
    ax.invert_yaxis()

    ax.set_xlabel(xlabel, color=COLOR_MUTED, fontsize=10)
    ax.set_title(title, color=COLOR_INK, fontsize=13, fontweight="bold", loc="left", pad=14)

    ax.grid(axis="x", color=COLOR_GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(COLOR_AXIS)
    ax.tick_params(axis="both", length=0, colors=COLOR_MUTED)

    for bar, count in zip(bars, counts):
        pct = count / total * 100
        ax.text(
            bar.get_width() + max_count * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({pct:.1f}%)",
            va="center",
            ha="left",
            fontsize=9.5,
            color=COLOR_INK,
        )

    ax.set_xlim(0, max_count * 1.18)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=SURFACE)
    plt.close(fig)
