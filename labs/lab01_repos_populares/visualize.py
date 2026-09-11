from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from shared.viz.charts import COLOR_GRID, COLOR_INK, COLOR_MUTED, SURFACE, fetch_distribution, plot_distribution

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
PARQUET_PATH = ROOT_DIR / "data" / "parquet" / "repositories.parquet"
ASSETS_DIR = REPO_ROOT / "docs" / "lab01" / "assets"

# (rotulo da faixa, condicao SQL sobre a view `repos`) -- faixas identicas
# as publicadas em docs/lab01/rq01_rq02_validacao.md e docs/lab01/rq03_rq04_validacao.md.
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
    "rq06_closed_issues": {
        "title": "RQ06 - Distribuicao do percentual de issues fechadas",
        "xlabel": "Repositorios",
        "buckets": [
            ("Sem issues", "total_issues_count = 0"),
            ("0-24%", "total_issues_count > 0 and closed_issues_ratio < 0.25"),
            ("25-49%", "closed_issues_ratio >= 0.25 and closed_issues_ratio < 0.50"),
            ("50-74%", "closed_issues_ratio >= 0.50 and closed_issues_ratio < 0.75"),
            ("75-89%", "closed_issues_ratio >= 0.75 and closed_issues_ratio < 0.90"),
            ("90-100%", "closed_issues_ratio >= 0.90"),
        ],
    },
}

COLOR_GROUP_POPULAR = "#2a78d6"
COLOR_GROUP_OTHER = "#eb6834"


def fetch_top_languages(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> list[tuple[str, int]]:
    query = f"""
        select coalesce(primary_language, 'Sem linguagem primaria') as lang, count(*) as total
        from repos
        group by 1
        order by total desc
        limit {limit}
    """
    return conn.execute(query).fetchall()


def plot_rq05_languages(conn: duckdb.DuckDBPyConnection, output_path: Path) -> None:
    rows = fetch_top_languages(conn)
    plot_distribution(
        rows,
        "RQ05 - Linguagens primarias mais frequentes",
        "Repositorios",
        output_path,
    )
    print(f"OK: {output_path} ({sum(count for _, count in rows)} repositorios)")


def fetch_language_group_medians(conn: duckdb.DuckDBPyConnection) -> dict[str, dict[str, float]]:
    query = """
        select
            case when is_popular_language then 'linguagem_popular' else 'outras_linguagens' end as grupo,
            median(accepted_pull_requests) as median_prs,
            median(releases_count) as median_releases,
            median(days_since_last_update) as median_dias
        from repos
        group by 1
    """
    rows = conn.execute(query).fetchall()
    return {grupo: {"prs": prs, "releases": releases, "dias": dias} for grupo, prs, releases, dias in rows}


def plot_rq07_comparison(conn: duckdb.DuckDBPyConnection, output_path: Path) -> None:
    medians = fetch_language_group_medians(conn)
    popular = medians["linguagem_popular"]
    other = medians["outras_linguagens"]

    metrics = [
        ("prs", "Mediana de PRs aceitas"),
        ("releases", "Mediana de releases"),
        ("dias", "Mediana de dias desde update"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(11, 4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    fig.suptitle(
        "RQ07 - Linguagens populares vs. demais linguagens",
        color=COLOR_INK,
        fontsize=13,
        fontweight="bold",
        x=0.02,
        ha="left",
    )

    labels = ["Linguagens\npopulares", "Demais\nlinguagens"]
    colors = [COLOR_GROUP_POPULAR, COLOR_GROUP_OTHER]

    for ax, (key, subtitle) in zip(axes, metrics):
        values = [popular[key], other[key]]
        ax.set_facecolor(SURFACE)
        bars = ax.bar(labels, values, width=0.55, color=colors, zorder=3)
        ax.set_title(subtitle, color=COLOR_INK, fontsize=10.5, pad=10)
        ax.grid(axis="y", color=COLOR_GRID, linewidth=1, zorder=0)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_color("#c3c2b7")
        ax.tick_params(axis="both", length=0, colors=COLOR_MUTED)
        max_value = max(values)
        ax.set_ylim(0, max_value * 1.22)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_value * 0.03,
                f"{value:,.1f}".replace(",", "."),
                ha="center",
                va="bottom",
                fontsize=9.5,
                color=COLOR_INK,
            )

    fig.tight_layout(rect=(0, 0, 1, 0.90))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=SURFACE)
    plt.close(fig)
    print(f"OK: {output_path}")


SPECIAL_CHARTS = ["rq05_language", "rq07_comparison"]
ALL_CHARTS = sorted(RQ_BUCKETS) + SPECIAL_CHARTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera graficos de distribuicao por faixa para as RQs do Lab01, a partir do parquet coletado."
    )
    parser.add_argument(
        "--rq",
        nargs="*",
        choices=ALL_CHARTS,
        default=ALL_CHARTS,
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
        if key == "rq05_language":
            plot_rq05_languages(conn, ASSETS_DIR / "rq05_language_distribuicao.png")
        elif key == "rq07_comparison":
            plot_rq07_comparison(conn, ASSETS_DIR / "rq07_comparacao.png")
        else:
            spec = RQ_BUCKETS[key]
            rows = fetch_distribution(conn, "repos", spec["buckets"])
            output_path = ASSETS_DIR / f"{key}_distribuicao.png"
            plot_distribution(rows, spec["title"], spec["xlabel"], output_path)
            print(f"OK: {output_path} ({sum(count for _, count in rows)} repositorios)")


if __name__ == "__main__":
    main()
