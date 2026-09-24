from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from labs.lab02_ia_vs_manual.analysis.data import KATA_CODES, KATAS, load_trials, validate
from labs.lab02_ia_vs_manual.analysis.stats import TREATMENTS, effect_size, summarize
from shared.viz.charts import COLOR_AXIS, COLOR_GRID, COLOR_INK, COLOR_MUTED, SURFACE

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "docs" / "lab02" / "assets"

COLORS = {"manual": "#2a78d6", "ai_assisted": "#e8833a"}
LABELS = {"manual": "Manual", "ai_assisted": "Com IA"}
TIMEBOX_MIN = 35

STATIC_METRICS = {
    "cyclomatic_complexity_avg": "Complexidade ciclomatica (media)",
    "maintainability_index": "Indice de manutenibilidade",
    "loc": "LOC (controle de verbosidade)",
    "duplication_pct": "Duplicacao (%)",
}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(COLOR_AXIS)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, colors=COLOR_MUTED)


def _new_figure(title: str, subtitle: str, width: float = 8.5, height: float = 5.0, **kwargs):
    fig, axes = plt.subplots(figsize=(width, height), dpi=150, **kwargs)
    fig.patch.set_facecolor(SURFACE)
    fig.suptitle(title, x=0.02, ha="left", fontsize=13, fontweight="bold", color=COLOR_INK)
    fig.text(0.02, 0.925, subtitle, ha="left", fontsize=9, color=COLOR_MUTED)
    return fig, axes


def _save(fig: plt.Figure, output_dir: Path, name: str, warning: str | None) -> Path:
    if warning:
        fig.text(0.5, 0.5, warning, ha="center", va="center", fontsize=26, color="#c0392b",
                 alpha=0.18, rotation=25, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path


def box_with_points(ax: plt.Axes, df: pd.DataFrame, column: str, ylabel: str, rng: np.random.Generator) -> None:
    """Boxplot (mediana/IQR) por tratamento com todos os pontos: mostra a amostra inteira."""
    _style(ax)
    groups = [df.loc[df["treatment"] == t, column].dropna().to_numpy() for t in TREATMENTS]
    ax.boxplot(
        groups, positions=range(len(TREATMENTS)), widths=0.45, showfliers=False, patch_artist=True,
        boxprops={"facecolor": "none", "edgecolor": COLOR_MUTED},
        medianprops={"color": COLOR_INK, "linewidth": 2},
        whiskerprops={"color": COLOR_MUTED}, capprops={"color": COLOR_MUTED}, zorder=2,
    )
    for position, (treatment, values) in enumerate(zip(TREATMENTS, groups)):
        ax.scatter(position + rng.uniform(-0.12, 0.12, values.size), values, s=34,
                   color=COLORS[treatment], alpha=0.85, zorder=3, edgecolor="white", linewidth=0.6)
        if values.size:
            ax.text(position + 0.27, np.median(values), f"mediana {np.median(values):.1f}",
                    fontsize=8, color=COLOR_INK, va="center", ha="left")
    ax.set_xticks(range(len(TREATMENTS)))
    ax.set_xticklabels([f"{LABELS[t]}\n(n={len(g)})" for t, g in zip(TREATMENTS, groups)], color=COLOR_INK)
    ax.set_xlim(-0.6, len(TREATMENTS) - 0.4)
    ax.set_ylabel(ylabel, color=COLOR_MUTED, fontsize=9)


def plot_rq1_time(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    fig, ax = _new_figure("RQ1 - Tempo ate passar nos testes", "Mediana e IQR por tratamento; cada ponto e um trial. X = censurado.")
    box_with_points(ax, df, "time_to_green_min", "Minutos", np.random.default_rng(0))
    ax.axhline(TIMEBOX_MIN, color="#c0392b", linestyle="--", linewidth=1)
    ax.text(ax.get_xlim()[1], TIMEBOX_MIN, " time-box 35 min", color="#c0392b", fontsize=8, va="bottom", ha="right")
    censored = df[df["censored"]]
    for treatment in TREATMENTS:
        rows = censored[censored["treatment"] == treatment]
        ax.scatter([TREATMENTS.index(treatment)] * len(rows), rows["time_to_green_min"], marker="x", s=60,
                   color="#c0392b", zorder=4)
    delta, magnitude = effect_size(df, "time_to_green_seconds")
    ax.set_title(f"Cliff's delta (IA vs manual) = {delta:.2f} ({magnitude})", loc="right", fontsize=9, color=COLOR_MUTED)
    return _save(fig, output_dir, "rq1_tempo_boxplot.png", warning)


def plot_rq1_by_kata(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    fig, ax = _new_figure("RQ1 - Tempo por kata e tratamento",
                          "Variacao de dificuldade entre katas e uma ameaca a validade: compare dentro do mesmo kata.", width=9.5)
    _style(ax)
    rng = np.random.default_rng(1)
    for treatment in TREATMENTS:
        rows = df[df["treatment"] == treatment]
        x = rows["kata"].map({kata: i for i, kata in enumerate(KATAS)}).to_numpy(dtype=float)
        ax.scatter(x + rng.uniform(-0.12, 0.12, len(rows)) + (0.14 if treatment == "ai_assisted" else -0.14),
                   rows["time_to_green_min"], s=42, color=COLORS[treatment], label=LABELS[treatment],
                   edgecolor="white", linewidth=0.6, zorder=3)
    ax.axhline(TIMEBOX_MIN, color="#c0392b", linestyle="--", linewidth=1)
    ax.set_xticks(range(len(KATAS)))
    ax.set_xticklabels([f"{KATA_CODES[k]}\n{k.replace('_', ' ')}" for k in KATAS], fontsize=7.5, color=COLOR_INK)
    ax.set_ylabel("Minutos", color=COLOR_MUTED, fontsize=9)
    ax.legend(frameon=False, loc="upper left")
    return _save(fig, output_dir, "rq1_tempo_por_kata.png", warning)


def plot_rq2_success(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    fig, ax = _new_figure("RQ2 - Trials com todos os testes passando", "Proporcao de trials verdes por tratamento (k de n); X testes falhando ao final somados.")
    _style(ax)
    for position, treatment in enumerate(TREATMENTS):
        rows = df[df["treatment"] == treatment]
        green = int((rows["tests_failed"] == 0).sum())
        rate = green / len(rows) if len(rows) else 0
        ax.bar(position, rate, width=0.5, color=COLORS[treatment], zorder=3)
        ax.text(position, rate + 0.02, f"{green}/{len(rows)} ({rate:.0%})\n{int(rows['tests_failed'].sum())} testes falhos",
                ha="center", fontsize=9, color=COLOR_INK)
    ax.set_ylim(0, 1.2)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(range(len(TREATMENTS)))
    ax.set_xticklabels([LABELS[t] for t in TREATMENTS], color=COLOR_INK)
    ax.set_xlim(-0.6, 1.6)
    return _save(fig, output_dir, "rq2_sucesso.png", warning)


def plot_rq3_boxplots(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    fig, axes = _new_figure("RQ3 - Metricas estaticas por tratamento", "Mediana e IQR; LOC ao lado como controle de verbosidade.",
                            width=9.5, height=7, nrows=2, ncols=2)
    rng = np.random.default_rng(2)
    for ax, (column, label) in zip(axes.flat, STATIC_METRICS.items()):
        box_with_points(ax, df, column, label, rng)
    return _save(fig, output_dir, "rq3_metricas_boxplot.png", warning)


def plot_rq3_loc_vs_complexity(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    fig, ax = _new_figure("RQ3 - Verbosidade x complexidade", "Se a diferenca de complexidade acompanha o LOC, e verbosidade e nao complexidade real.")
    _style(ax)
    for treatment in TREATMENTS:
        rows = df[df["treatment"] == treatment]
        ax.scatter(rows["loc"], rows["cyclomatic_complexity_avg"], s=48, color=COLORS[treatment],
                   label=LABELS[treatment], edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xlabel("LOC", color=COLOR_MUTED, fontsize=9)
    ax.set_ylabel("Complexidade ciclomatica (media)", color=COLOR_MUTED, fontsize=9)
    ax.legend(frameon=False)
    return _save(fig, output_dir, "rq3_loc_vs_complexidade.png", warning)


def plot_metric_correlation(df: pd.DataFrame, output_dir: Path, warning: str | None) -> Path:
    columns = {**STATIC_METRICS, "time_to_green_seconds": "Tempo ate verde"}
    corr = df[list(columns)].corr(method="spearman")
    fig, ax = _new_figure("Correlacao de Spearman entre metricas", "Blocos vermelhos indicam metricas redundantes (multicolinearidade).", width=7.5, height=6)
    image = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(columns)))
    ax.set_yticks(range(len(columns)))
    ax.set_xticklabels(list(columns.values()), rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(list(columns.values()), fontsize=8)
    for i in range(len(columns)):
        for j in range(len(columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(corr.iloc[i, j]) > 0.6 else COLOR_INK)
    fig.colorbar(image, ax=ax, shrink=0.8)
    return _save(fig, output_dir, "correlacao_metricas.png", warning)


def build_dashboard(df: pd.DataFrame, output_dir: Path, warning: str | None) -> list[Path]:
    plots = [plot_rq1_time, plot_rq1_by_kata, plot_rq2_success, plot_rq3_boxplots,
             plot_rq3_loc_vs_complexity, plot_metric_correlation]
    return [plot(df, output_dir, warning) for plot in plots]


def print_summary(df: pd.DataFrame) -> None:
    for column in ("time_to_green_seconds", "acceptance_success_rate", *STATIC_METRICS):
        print(f"\n{column}")
        print(summarize(df, column).round(2).to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera os graficos do dashboard do Lab02.")
    parser.add_argument("--sample", action="store_true", help="Usa trials_sample.jsonl (sintetico) so para testar.")
    parser.add_argument("--output-dir", type=Path, default=None, help=f"Default: {ASSETS_DIR} (ou .../sample com --sample).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_trials(sample=args.sample)
    if df.empty:
        raise SystemExit("Nenhum trial encontrado em labs/lab02_ia_vs_manual/data/raw.")

    problems = validate(df, sample=args.sample)
    for problem in problems:
        print(f"AVISO: {problem}")
    warning = "SINTETICO" if args.sample else ("PRELIMINAR" if problems else None)

    output_dir = args.output_dir or (ASSETS_DIR / "sample" if args.sample else ASSETS_DIR)
    print_summary(df)
    for path in build_dashboard(df, output_dir, warning):
        print(f"OK: {path}")


if __name__ == "__main__":
    main()
