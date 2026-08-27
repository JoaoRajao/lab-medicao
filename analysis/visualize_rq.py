from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
PARQUET_PATH = ROOT_DIR / "github_ingest" / "data" / "parquet" / "repositories.parquet"
ASSETS_DIR = ROOT_DIR / "docs" / "assets"

COLOR_BAR = "#2a78d6"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_INK = "#0b0b0b"
COLOR_MUTED = "#898781"
SURFACE = "#fcfcfb"

# (rotulo da faixa, condicao SQL sobre a view `repos`) -- faixas identicas
# as publicadas em docs/rq01_rq02_validacao.md e docs/rq03_rq04_validacao.md.
RQ_BUCKETS: dict[str, dict] = {
    "rq01_age": {
        "title": "RQ01 - Distribuicao da idade dos repositorios",
        "xlabel": "Repositorios",
        "buckets": [
            ("Menos de 1 ano (< 365 dias)", "age_days < 365"),
            ("1 a 3 anos (365-1.095 dias)", "age_days >= 365 and age_days < 1095"),
            ("3 a 5 anos (1.095-1.825 dias)", "age_days >= 1095 and age_days < 1825"),
            ("5 a 10 anos (1.825-3.650 dias)", "age_days >= 1825 and age_days <= 3650"),
            ("Mais de 10 anos (> 3.650 dias)", "age_days > 3650"),
        ],
    },
    "rq02_pull_requests": {
        "title": "RQ02 - Distribuicao de pull requests aceitas",
        "xlabel": "Repositorios",
        "buckets": [
            ("Sem PRs aceitos (0)", "accepted_pull_requests = 0"),
            ("Poucos PRs (1-99)", "accepted_pull_requests >= 1 and accepted_pull_requests < 100"),
            ("Moderado (100-499)", "accepted_pull_requests >= 100 and accepted_pull_requests < 500"),
            ("Alto (500-1.999)", "accepted_pull_requests >= 500 and accepted_pull_requests < 2000"),
            ("Muito alto (>= 2.000)", "accepted_pull_requests >= 2000"),
        ],
    },
    "rq03_releases": {
        "title": "RQ03 - Distribuicao de releases lancadas",
        "xlabel": "Repositorios",
        "buckets": [
            ("Sem releases (0)", "releases_count = 0"),
            ("Poucas releases (1-9)", "releases_count >= 1 and releases_count < 10"),
            ("Moderado (10-49)", "releases_count >= 10 and releases_count < 50"),
            ("Frequente (50-199)", "releases_count >= 50 and releases_count < 200"),
            ("Muito frequente (>= 200)", "releases_count >= 200"),
        ],
    },
    "rq04_updates": {
        "title": "RQ04 - Distribuicao de dias desde a ultima atualizacao",
        "xlabel": "Repositorios",
        "buckets": [
            ("Muito Recente (0-7 dias)", "days_since_last_update >= 0 and days_since_last_update <= 7"),
            ("Recente (8-30 dias)", "days_since_last_update >= 8 and days_since_last_update <= 30"),
            ("Medio Prazo (31-90 dias)", "days_since_last_update >= 31 and days_since_last_update <= 90"),
            ("Longo Prazo (91-365 dias)", "days_since_last_update >= 91 and days_since_last_update <= 365"),
            ("Inativo (> 365 dias)", "days_since_last_update > 365"),
        ],
    },
}


def fetch_distribution(conn: duckdb.DuckDBPyConnection, buckets: list[tuple[str, str]]) -> list[tuple[str, int]]:
    selects = [
        f"select '{label}' as faixa, count(*) as total, {index} as ord from repos where {condition}"
        for index, (label, condition) in enumerate(buckets)
    ]
    query = " union all ".join(selects) + " order by ord"
    rows = conn.execute(query).fetchall()
    return [(label, total) for label, total, _ in rows]


def plot_distribution(rows: list[tuple[str, int]], title: str, xlabel: str, output_path: Path) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera graficos de distribuicao por faixa para as RQs, a partir do parquet coletado."
    )
    parser.add_argument(
        "--rq",
        nargs="*",
        choices=sorted(RQ_BUCKETS),
        default=sorted(RQ_BUCKETS),
        help="Quais RQs gerar (default: todas as configuradas).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not PARQUET_PATH.exists():
        raise RuntimeError(f"Parquet nao encontrado em {PARQUET_PATH}. Rode a ingestao antes.")

    conn = duckdb.connect()
    conn.execute(f"create view repos as select * from read_parquet('{PARQUET_PATH.as_posix()}')")

    for key in args.rq:
        spec = RQ_BUCKETS[key]
        rows = fetch_distribution(conn, spec["buckets"])
        output_path = ASSETS_DIR / f"{key}_distribuicao.png"
        plot_distribution(rows, spec["title"], spec["xlabel"], output_path)
        print(f"OK: {output_path} ({sum(count for _, count in rows)} repositorios)")


if __name__ == "__main__":
    main()
